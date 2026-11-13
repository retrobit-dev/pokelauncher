package dev.retrobit.pokelauncher.ui

import android.content.Context
import android.graphics.BitmapFactory
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import dev.retrobit.pokelauncher.game.Camera
import dev.retrobit.pokelauncher.game.CameraRig
import dev.retrobit.pokelauncher.game.Direction
import dev.retrobit.pokelauncher.game.GameClock
import dev.retrobit.pokelauncher.game.GameMap
import dev.retrobit.pokelauncher.game.MapJson
import dev.retrobit.pokelauncher.game.Pathfinder
import dev.retrobit.pokelauncher.game.TileSet
import dev.retrobit.pokelauncher.game.World
import dev.retrobit.pokelauncher.game.WorldState
import dev.retrobit.pokelauncher.data.WorldStore
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
    private val store = WorldStore(appContext)

    private val _state = MutableStateFlow(GameUiState())
    val state: StateFlow<GameUiState> = _state.asStateFlow()

    private var walkJob: Job? = null

    /**
     * Bumped on every new walk. A cancelled job clears the walk flags in its
     * `finally`, and cancellation is cooperative: without this token that
     * cleanup could land after the replacement job started and stop its legs.
     */
    private var walkToken = 0
    private var cameraJob: Job? = null
    private var rig: CameraRig? = null
    private val utcOffsetMinutes: Int
        get() = TimeZone.getDefault().getOffset(System.currentTimeMillis()) / 60_000

    init {
        val world = World(map, tiles)
        val clockAtLaunch = currentClock()
        restoreWorld(world)
        world.waterDay = dayOf()

        val rig = CameraRig(
            viewWidth = 2560,
            viewHeight = 1600,
            mapWidth = map.widthPx,
            mapHeight = map.heightPx,
            startX = world.playerX * GameMap.TILE,
            startY = world.playerY * GameMap.TILE,
        )
        this.rig = rig

        _state.value = GameUiState(
            ready = true,
            tiles = tiles,
            map = map,
            atlas = loadAtlas(),
            playerSheet = loadPlayerSheet(),
            world = world,
            clock = clockAtLaunch,
            day = dayOf(),
            camera = Camera(
                viewWidth = 2560,
                viewHeight = 1600,
                mapWidth = map.widthPx,
                mapHeight = map.heightPx,
            ),
            scale = 3,
        )
        startSurvivalLoop()
        startCameraLoop()
    }

    /**
     * The camera runs on its own clock.
     *
     * Walking is stepped (one cell per tick) but the camera is not: at 60 fps a
     * follow that only moved on a cell boundary would look like a series of
     * jerks. This loop advances the rig every frame and publishes the window
     * only when it actually moved, so a still camera costs no recomposition.
     */
    private fun startCameraLoop() {
        cameraJob?.cancel()
        cameraJob = viewModelScope.launch {
            while (true) {
                val current = _state.value
                val world = current.world
                val r = rig
                if (world != null && r != null &&
                    (current.viewWidth != r.viewWidth || current.viewHeight != r.viewHeight)
                ) {
                    r.resize(current.viewWidth, current.viewHeight, map.widthPx, map.heightPx)
                    r.jumpTo(world.playerX * GameMap.TILE, world.playerY * GameMap.TILE)
                }
                val moved = r?.advance(
                    (world?.playerX ?: 0) * GameMap.TILE,
                    (world?.playerY ?: 0) * GameMap.TILE,
                ) ?: false
                if (moved && r != null) {
                    _state.value = _state.value.copy(
                        camera = r.camera(),
                        revision = _state.value.revision + 1,
                    )
                }
                delay(CAMERA_FRAME_MILLIS)
            }
        }
    }

    /**
     * The Compose view is the only thing that knows the real panel size, so it
     * reports it here instead of the rig guessing 2560x1600 forever.
     */
    fun onViewportChanged(widthPx: Int, heightPx: Int, scale: Int) {
        val current = _state.value
        if (current.viewWidth == widthPx && current.viewHeight == heightPx && current.scale == scale) return
        _state.value = current.copy(viewWidth = widthPx, viewHeight = heightPx, scale = scale)
    }

    private fun currentClock(): GameClock =
        GameClock.fromMillisUtc(System.currentTimeMillis(), utcOffsetMinutes)

    /**
     * Restores the last save, if it still makes sense for this map.
     *
     * A save from an older map version is dropped rather than applied: the map
     * is authored content, and a player standing where a wall now is would be
     * stuck. Restoring is silent; losing a field is not worth a dialog.
     */
    private fun restoreWorld(world: World) {
        val json = store.load() ?: return
        val parsed = WorldState.fromJson(json, world, fallbackDay = dayOf()) ?: return
        WorldState.restore(parsed.snapshot, world)
    }

    /** Called after anything that changes the save-worthy world. */
    private fun persist() {
        val world = _state.value.world ?: return
        store.save(WorldState.toJson(WorldState.snapshot(world, dayOf()), System.currentTimeMillis()))
    }

    /** Whole days since the epoch in local time, the unit crops age in. */
    private fun dayOf(): Int =
        ((System.currentTimeMillis() + utcOffsetMinutes * 60_000L) / 86_400_000L).toInt()

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
     * The walk sheet is optional on purpose: a missing or undecodable sprite
     * must not stop the world from loading, so the canvas falls back to the
     * ink silhouette it drew before the art existed.
     */
    private fun loadPlayerSheet(): ImageBitmap? = runCatching {
        appContext.assets.open("sprites/player.png").use { stream ->
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
                // Watering is once per real day: the day counter the crops use
                // is the same one the sun uses, so a session cannot water twice.
                world.waterDay = dayOf()
                val tick = world.tickSurvival(clock, minutes = 1)
                val fainted = world.faintIfDead()
                _state.value = current.copy(
                    clock = clock,
                    day = dayOf(),
                    tick = tick,
                    revision = current.revision + 1,
                    message = if (fainted) "Kau pingsan. Bangun di rumah, sebagian barang hilang." else current.message,
                    messageId = if (fainted) current.messageId + 1 else current.messageId,
                )
                persist()
            }
        }
    }

    fun tapCell(cellX: Int, cellY: Int) {
        val current = _state.value
        current.world?.waterDay = dayOf()
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

        val token = ++walkToken
        walkJob = viewModelScope.launch {
            try {
                for ((x, y) in path) {
                    val current = _state.value
                    val w = current.world ?: break
                    val direction = Direction.toward(w.playerX, w.playerY, x, y)
                    if (!w.step(direction)) break // someone blocked us: stop cleanly
                    _state.value = current.copy(
                        revision = current.revision + 1,
                        walking = true,
                        stepParity = !current.stepParity,
                    )
                    delay(STEP_MILLIS)
                }
            } finally {
                // Also runs when a new tap cancels this job mid-path: the legs
                // must not be left in mid-stride after the walk is abandoned.
                if (token == walkToken) {
                    _state.value = _state.value.copy(walking = false, stepParity = false)
                }
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
        val today = current.day

        // Priority follows what the player is looking at: a ripe crop first,
        // then bare soil to sow, then the block itself to mine.
        val crop = world.cropAt(x, y)
        val message = when {
            crop != null && crop.isRipe(today) -> {
                val yield = world.harvest(x, y, today)
                if (yield > 0) "Panen +$yield makanan" else null
            }
            crop != null ->
                if (world.water(x, y)) "Padi disiram (${crop.growth + 1}/${World.DAYS_TO_RIPE})" else "Sudah disiram hari ini"
            world.isTilled(x, y) ->
                if (world.plant(x, y, today)) "Bibit ditanam" else "Bibit habis"
            else -> when (val mined = world.mine(x, y)) {
                is World.MineResult.Mined -> mined.drop?.let { "Dapat ${it.label}" } ?: "Dibersihkan"
                World.MineResult.TooFar -> "Terlalu jauh"
                World.MineResult.Nothing -> null
            }
        }

        _state.value = current.copy(
            revision = current.revision + 1,
            message = message ?: current.message,
            messageId = if (message != null) current.messageId + 1 else current.messageId,
        )
        persist()
    }

    fun useUnderfoot() {
        val current = _state.value
        val world = current.world ?: return
        val today = current.day
        val x = world.playerX
        val y = world.playerY
        // One button, Harvest Moon style: do the obvious next thing where you
        // stand, then in front of you. Watering comes before tilling so a crop
        // is never buried under new soil.
        val targets = listOf(x to y, x + world.facing.dx to y + world.facing.dy)
        var message: String? = null
        for ((tx, ty) in targets) {
            val crop = world.cropAt(tx, ty)
            message = when {
                crop != null && crop.isRipe(today) -> {
                    val yield = world.harvest(tx, ty, today)
                    if (yield > 0) "Panen +$yield makanan" else null
                }
                crop != null -> if (world.water(tx, ty)) {
                    "Disiram (${world.cropAt(tx, ty)?.growth ?: 0}/${World.DAYS_TO_RIPE})"
                } else {
                    "Sudah disiram hari ini"
                }
                world.isTilled(tx, ty) ->
                    if (world.plant(tx, ty, today)) "Bibit ditanam" else "Bibit habis"
                world.till(tx, ty) -> "Tanah dibajak"
                else -> null
            }
            if (message != null) break
        }
        _state.value = current.copy(
            revision = current.revision + 1,
            message = message ?: current.message,
            messageId = if (message != null) current.messageId + 1 else current.messageId,
        )
        persist()
    }

    /** The HUD's MAKAN button. */
    fun eat() {
        val current = _state.value
        if (current.world?.eat() == true) {
            _state.value = current.copy(
                revision = current.revision + 1,
                message = "Kenyang +${World.FOOD_VALUE}",
                messageId = current.messageId + 1,
            )
            persist()
        } else {
            _state.value = current.copy(
                message = if (current.world?.hunger == World.MAX_HUNGER) "Belum lapar" else "Makanan habis",
                messageId = current.messageId + 1,
            )
        }
    }

    /** The HUD's LAMPU button: craft one from what you mined, then place it. */
    fun craftLight() {
        val current = _state.value
        val world = current.world ?: return
        if (world.torches > 0) {
            placeLight()
            return
        }
        if (world.craftTorch()) {
            _state.value = current.copy(
                revision = current.revision + 1,
                message = "Lampu dibuat (batu + serat)",
                messageId = current.messageId + 1,
            )
            persist()
        } else {
            _state.value = current.copy(
                message = "Butuh 1 batu + 1 serat",
                messageId = current.messageId + 1,
            )
        }
    }

    fun placeLight() {
        val current = _state.value
        if (current.world?.placeLight() == true) {
            _state.value = current.copy(
                revision = current.revision + 1,
                message = "Lampu dipasang",
                messageId = current.messageId + 1,
            )
            persist()
        } else {
            _state.value = current.copy(
                message = if (current.world?.torches == 0) "Tidak punya lampu" else "Sudah ada lampu di sini",
                messageId = current.messageId + 1,
            )
        }
    }

    fun buildStone() {
        val current = _state.value
        if (current.world?.build(World.Item.STONE) is World.BuildResult.Built) {
            _state.value = current.copy(revision = current.revision + 1)
            persist()
        }
    }

    fun zoomBy(step: Int) {
        val current = _state.value
        val steps = dev.retrobit.pokelauncher.game.TouchInput.STEPS
        val index = steps.indexOf(current.scale).coerceAtLeast(0) + step
        val next = steps[index.coerceIn(steps.indices)]
        // A zoomed panel shows fewer map pixels, so the window shrinks with it.
        rig?.resize(
            viewWidth = (current.viewWidth * current.scale / next).coerceAtLeast(GameMap.TILE),
            viewHeight = (current.viewHeight * current.scale / next).coerceAtLeast(GameMap.TILE),
            mapWidth = map.widthPx,
            mapHeight = map.heightPx,
        )
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

        /** ~60 fps. One frame of camera movement is a few map pixels. */
        const val CAMERA_FRAME_MILLIS = 16L
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
    /** Whole real days since the epoch; crops age in this unit. */
    val day: Int = 0,
    val camera: Camera = Camera(viewWidth = 2560, viewHeight = 1600, mapWidth = 16, mapHeight = 16),
    /** Panel size in pixels, reported by Compose; the rig reads it. */
    val viewWidth: Int = 2560,
    val viewHeight: Int = 1600,
    val scale: Int = 3,
    val revision: Int = 0,
    /** Walk sheet, 2 frames x 4 directions; null if the asset is missing. */
    val playerSheet: ImageBitmap? = null,
    /**
     * Flips on every step, so the sprite alternates between its two frames.
     * Derived from the step counter rather than a wall clock: a timer would
     * keep the legs moving while the player stands still.
     */
    val stepParity: Boolean = false,
    /** True while a walk is in progress, so frame 0 is used at rest. */
    val walking: Boolean = false,
    val tick: World.SurvivalTick? = null,
    /** Last one-line answer from the world, shown briefly by the HUD. */
    val message: String? = null,
    /** Changes on every new message, so the HUD can restart its timer. */
    val messageId: Int = 0,
)
