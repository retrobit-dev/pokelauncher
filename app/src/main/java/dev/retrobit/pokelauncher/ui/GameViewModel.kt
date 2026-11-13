package dev.retrobit.pokelauncher.ui

import android.content.Context
import android.graphics.BitmapFactory
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import dev.retrobit.pokelauncher.game.Camera
import dev.retrobit.pokelauncher.game.Direction
import dev.retrobit.pokelauncher.game.GameClock
import dev.retrobit.pokelauncher.game.GameMap
import dev.retrobit.pokelauncher.game.MapJson
import dev.retrobit.pokelauncher.game.Pathfinder
import dev.retrobit.pokelauncher.game.TileSet
import dev.retrobit.pokelauncher.game.World
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.util.TimeZone

/**
 * Holds the world between recompositions and drives walking.
 *
 * The world itself is plain Kotlin ([World]); this class only owns what is
 * Android-shaped: the atlas bitmap, the real clock, and the coroutine that walks
 * the player one cell at a time.
 *
 * Walking is stepped rather than animated on purpose: one cell per tick is what
 * HeartGold does, it keeps collision honest (every step is checked), and it
 * means a dropped frame never moves the character through a wall.
 */
class GameViewModel(context: Context) : ViewModel() {

    private val appContext = context.applicationContext

    private val tiles: TileSet = loadTiles()
    private val map: GameMap = loadMap(tiles)

    private val _state = MutableStateFlow(GameUiState())
    val state: StateFlow<GameUiState> = _state.asStateFlow()

    private var walkJob: Job? = null
    private val utcOffsetMinutes: Int
        get() = TimeZone.getDefault().getOffset(System.currentTimeMillis()) / 60_000

    init {
        _state.value = GameUiState(
            ready = true,
            tiles = tiles,
            map = map,
            atlas = loadAtlas(),
            world = World(map, tiles),
            clock = currentClock(),
            camera = Camera(
                viewWidth = 2560,
                viewHeight = 1600,
                mapWidth = map.widthPx,
                mapHeight = map.heightPx,
            ),
            scale = 3,
        )
        startSurvivalLoop()
    }

    private fun currentClock(): GameClock =
        GameClock.fromMillisUtc(System.currentTimeMillis(), utcOffsetMinutes)

    private fun loadTiles(): TileSet = runCatching {
        appContext.assets.open("tileset/tileset.json").bufferedReader().use { it.readText() }
            .let(MapJson::parseTileSet)
    }.getOrElse { emptyTileSet() }

    private fun loadMap(tiles: TileSet): GameMap = runCatching {
        val json = appContext.assets.open("tileset/map.json").bufferedReader().use { it.readText() }
        MapJson.parseMap(json, tiles)
    }.getOrElse { starterMap() }

    private fun loadAtlas(): ImageBitmap? = runCatching {
        appContext.assets.open("tileset/johto-tileset.png").use { stream ->
            BitmapFactory.decodeStream(stream)?.asImageBitmap()
        }
    }.getOrNull()

    /**
     * The sun moves, hunger drains and the night bites. One tick a minute is
     * enough for all three and costs almost nothing while the tablet idles.
     */
    private fun startSurvivalLoop() {
        viewModelScope.launch {
            while (true) {
                delay(60_000L)
                val current = _state.value
                val clock = currentClock()
                val world = current.world ?: continue
                val tick = world.tickSurvival(clock, minutes = 1)
                _state.value = current.copy(
                    clock = clock,
                    tick = tick,
                    revision = current.revision + 1,
                )
            }
        }
    }

    fun tapCell(cellX: Int, cellY: Int) {
        val current = _state.value
        val world = current.world ?: return

        if (cellX == world.playerX && cellY == world.playerY) {
            useUnderfoot()
            return
        }

        // Already beside a solid target and facing it: act instead of walking,
        // so chipping at a tree does not need two taps each time.
        val adjacent = Math.abs(cellX - world.playerX) + Math.abs(cellY - world.playerY) == 1
        val solid = !world.canStand(cellX, cellY)
        if (adjacent && solid) {
            actOn(cellX, cellY)
            return
        }

        walkTo(cellX, cellY)
    }

    private fun walkTo(goalX: Int, goalY: Int) {
        walkJob?.cancel()
        val world = _state.value.world ?: return
        val path = Pathfinder.find(world.playerX, world.playerY, goalX, goalY) { x, y ->
            world.canStand(x, y)
        }
        if (path.isEmpty()) return

        walkJob = viewModelScope.launch {
            for ((x, y) in path) {
                val current = _state.value
                val w = current.world ?: break
                val direction = Direction.toward(w.playerX, w.playerY, x, y)
                if (!w.step(direction)) break // someone blocked us: stop cleanly
                val camera = current.camera.follow(w.playerX * GameMap.TILE, w.playerY * GameMap.TILE)
                _state.value = current.copy(camera = camera, revision = current.revision + 1)
                delay(STEP_MILLIS)
            }
            onArrived()
        }
    }

    /** Reaching a target should not require a second tap to act on it. */
    private fun onArrived() {
        val current = _state.value
        val w = current.world ?: return
        val frontX = w.playerX + w.facing.dx
        val frontY = w.playerY + w.facing.dy
        if (!w.canStand(frontX, frontY)) actOn(frontX, frontY) else useUnderfoot()
    }

    private fun actOn(x: Int, y: Int) {
        val current = _state.value
        val world = current.world ?: return
        val today = current.clock.minuteOfDay / 1440

        // Priority follows what the player is looking at: a ripe crop first,
        // then bare soil to sow, then the block itself to mine.
        val crop = world.cropAt(x, y)
        val acted = when {
            crop != null && crop.isRipe(today) -> world.harvest(x, y, today) > 0
            world.isTilled(x, y) && world.cropAt(x, y) == null -> world.plant(x, y, today)
            else -> world.mine(x, y) is World.MineResult.Mined
        }
        if (!acted) world.mine(x, y) // a last attempt so a plain wall still gives feedback

        _state.value = current.copy(revision = current.revision + 1)
    }

    private fun useUnderfoot() {
        val current = _state.value
        val world = current.world ?: return
        val today = current.clock.minuteOfDay / 1440
        val x = world.playerX
        val y = world.playerY
        val acted = when {
            world.cropAt(x, y)?.let { it.isRipe(today) } == true -> world.harvest(x, y, today) > 0
            world.isTilled(x, y) && world.cropAt(x, y) == null -> world.plant(x, y, today)
            else -> world.till(x, y)
        }
        if (!acted) world.eat()
        _state.value = current.copy(revision = current.revision + 1)
    }

    fun placeLight() {
        val current = _state.value
        if (current.world?.placeLight() == true) {
            _state.value = current.copy(revision = current.revision + 1)
        }
    }

    fun buildStone() {
        val current = _state.value
        if (current.world?.build(World.Item.STONE) is World.BuildResult.Built) {
            _state.value = current.copy(revision = current.revision + 1)
        }
    }

    fun zoomBy(step: Int) {
        val current = _state.value
        val steps = dev.retrobit.pokelauncher.game.TouchInput.STEPS
        val index = steps.indexOf(current.scale).coerceAtLeast(0) + step
        val next = steps[index.coerceIn(steps.indices)]
        _state.value = current.copy(scale = next, revision = current.revision + 1)
    }

    /** The launcher opens only beside the machine: it is a place in the world. */
    fun nearMachine(): Boolean {
        val current = _state.value
        val w = current.world ?: return false
        for (dx in -1..1) {
            for (dy in -1..1) {
                val cell = current.map.cell(w.playerX + dx, w.playerY + dy) ?: continue
                val name = cell.objectTile ?: continue
                if (name.startsWith("machine")) return true
            }
        }
        return false
    }

    private fun emptyTileSet(): TileSet =
        TileSet(GameMap.TILE, 8, mapOf("grass" to TileSet.Tile("grass", 0, 0, 16, 16, false, "ground")))

    /** A tiny lawn so the home screen still works before a map is authored. */
    private fun starterMap(): GameMap {
        val cols = 40
        val rows = 25
        val cells = HashMap<Long, dev.retrobit.pokelauncher.game.Cell>()
        for (y in 0 until rows) {
            for (x in 0 until cols) {
                cells[GameMap.key(x, y)] = dev.retrobit.pokelauncher.game.Cell(ground = "grass")
            }
        }
        return GameMap.fromCells(cols, rows, cells, spawnX = cols / 2, spawnY = rows / 2)
    }

    class Factory(private val context: Context) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            GameViewModel(context) as T
    }

    companion object {
        const val STEP_MILLIS = 140L
    }
}

/**
 * One immutable snapshot of everything the world screen draws.
 *
 * A single state object (rather than a dozen mutable fields) is what makes the
 * Compose layer simple: one recomposition trigger, one camera, one revision
 * counter to force a redraw after the world mutates in place.
 */
data class GameUiState(
    val ready: Boolean = false,
    val tiles: TileSet = TileSet(16, 8, emptyMap()),
    val map: GameMap = GameMap.fromCells(1, 1, emptyMap()),
    val atlas: ImageBitmap? = null,
    val world: World? = null,
    val clock: GameClock = GameClock.atMinute(12 * 60),
    val camera: Camera = Camera(viewWidth = 2560, viewHeight = 1600, mapWidth = 16, mapHeight = 16),
    val scale: Int = 3,
    val revision: Int = 0,
    val tick: World.SurvivalTick? = null,
)
