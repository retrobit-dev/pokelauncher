package dev.retrobit.pokelauncher.game

/**
 * The parts of the world that change while you play.
 *
 * Deliberately a plain state machine: no Android, no coroutines, no drawing.
 * The screen reads this, the touch handler sends commands, and every rule below
 * can be tested on the JVM. That split is what makes a game this size keepable:
 * the picture can change without ever putting a bug in the economy.
 */
class World(
    val map: GameMap,
    val tiles: TileSet,
    startX: Int = map.spawnX,
    startY: Int = map.spawnY,
) {
    var playerX = startX
        private set
    var playerY = startY
        private set

    /** Facing, for the sprite and for "use what is in front of me". */
    var facing: Direction = Direction.DOWN
        private set

    var health = MAX_HEALTH
        private set
    var hunger = MAX_HUNGER
        private set

    /** Light the player placed: night is survivable where there is a light. */
    private val lights = HashSet<Long>()

    /** Cells cleared by mining; they are no longer solid and no longer drawn. */
    private val cleared = HashSet<Long>()

    private val crops = LinkedHashMap<Long, Crop>()

    val wood: Int get() = inventory[Item.WOOD] ?: 0
    val stone: Int get() = inventory[Item.STONE] ?: 0
    val fibre: Int get() = inventory[Item.FIBRE] ?: 0
    val food: Int get() = inventory[Item.FOOD] ?: 0
    val seeds: Int get() = inventory[Item.SEED] ?: 0

    private val inventory = HashMap<Item, Int>()

    init {
        inventory[Item.WOOD] = 8
        inventory[Item.STONE] = 4
        inventory[Item.FIBRE] = 2
        inventory[Item.SEED] = 3
        inventory[Item.FOOD] = 1
    }

    // ---------------------------------------------------------------- walking

    /**
     * Take one step if the target cell can be stood on.
     *
     * Turning always works, walking into a wall still turns you to face it:
     * that is how the game answers a tap toward a tree without feeling dead.
     */
    fun step(direction: Direction): Boolean {
        facing = direction
        val nx = playerX + direction.dx
        val ny = playerY + direction.dy
        if (!canStand(nx, ny)) return false
        playerX = nx
        playerY = ny
        return true
    }

    fun canStand(x: Int, y: Int): Boolean {
        if (!map.inBounds(x, y)) return false
        val k = GameMap.key(x, y)
        if (cleared.contains(k)) return false      // mined out: a hole
        if (built.containsKey(k)) return false     // your own block is a wall too
        return !map.isSolid(x, y, tiles)
    }

    // ---------------------------------------------------------------- building

    /**
     * Minecraft's builder core: the world is made of cells you can remove and
     * put back. Mining yields materials; building spends them.
     *
     * Mining a solid cell removes whatever was on top of it and returns what it
     * was made of. Grass and paths are not minable: stripping the ground would
     * leave a hole in the map, not a resource.
     *
     * The result carries the cell, because the UI needs to know *which* block
     * was hit: tapping a neighbour must not mine the one you stand on.
     */
    fun mine(x: Int, y: Int): MineResult {
        if (!map.inBounds(x, y)) return MineResult.Nothing
        val k = GameMap.key(x, y)
        if (cleared.contains(k)) return MineResult.Nothing
        if (distanceTo(x, y) > REACH) return MineResult.TooFar

        val cell = map.cell(x, y) ?: return MineResult.Nothing
        val target = cell.objectTile ?: cell.building ?: cell.ground
        val tile = target?.let { tiles[it] } ?: return MineResult.Nothing
        if (!tile.solid) return MineResult.Nothing
        if (tile.name.startsWith("water")) return MineResult.Nothing // dig the bank, not the pond

        val drop = dropFor(tile.name)
        cleared.add(k)
        if (drop != null) inventory[drop] = (inventory[drop] ?: 0) + 1
        return MineResult.Mined(tile.name, drop, x, y)
    }

    /** Places a block in front of the player, spending one material. */
    fun build(item: Item): BuildResult {
        if (!item.isBlock) return BuildResult.NotABlock
        val x = playerX + facing.dx
        val y = playerY + facing.dy
        if (!map.inBounds(x, y)) return BuildResult.Blocked
        if ((inventory[item] ?: 0) <= 0) return BuildResult.NoMaterial
        val k = GameMap.key(x, y)
        if (x == playerX && y == playerY) return BuildResult.Blocked

        inventory[item] = (inventory[item] ?: 0) - 1
        built[k] = item
        cleared.remove(k)
        return BuildResult.Built(item, x, y)
    }

    /** What the player built, drawn above the map tiles. */
    private val built = LinkedHashMap<Long, Item>()

    fun builtAt(x: Int, y: Int): Item? = built[GameMap.key(x, y)]

    /**
     * Makes a torch from a stone and a fibre.
     *
     * Crafting is one recipe on purpose: the point is that surviving the night
     * costs something you gathered, not that the game grows a crafting tree.
     */
    fun craftTorch(): Boolean {
        if ((inventory[Item.STONE] ?: 0) < 1) return false
        if ((inventory[Item.FIBRE] ?: 0) < 1) return false
        inventory[Item.STONE] = (inventory[Item.STONE] ?: 0) - 1
        inventory[Item.FIBRE] = (inventory[Item.FIBRE] ?: 0) - 1
        inventory[Item.TORCH] = (inventory[Item.TORCH] ?: 0) + 1
        return true
    }

    /** A light source makes the surrounding cells safe at night. */
    fun placeLight(): Boolean {
        if ((inventory[Item.TORCH] ?: 0) <= 0) return false
        val k = GameMap.key(playerX, playerY)
        if (lights.contains(k)) return false
        inventory[Item.TORCH] = (inventory[Item.TORCH] ?: 0) - 1
        lights.add(k)
        return true
    }

    fun isLit(x: Int, y: Int): Boolean =
        lights.any { l ->
            val lx = (l shr 32).toInt()
            val ly = (l and 0xFFFFFFFFL).toInt()
            Math.abs(lx - x) <= LIGHT_RADIUS && Math.abs(ly - y) <= LIGHT_RADIUS
        }

    // ---------------------------------------------------------------- farming

    /**
     * Farming is Harvest Moon by way of Minecraft: till a cell, plant a seed,
     * water it, and it grows over real days. The clock is the challenge; you
     * cannot wait a season out in one session.
     */
    fun till(x: Int, y: Int): Boolean {
        if (distanceTo(x, y) > REACH) return false
        if (!map.inBounds(x, y)) return false
        val cell = map.cell(x, y) ?: return false
        val ground = cell.ground ?: return false
        if (ground != "grass" && ground != "grass_detail" && ground != "grass_dark") return false
        if (cell.objectTile != null || cell.building != null) return false
        tilled.add(GameMap.key(x, y))
        return true
    }

    private val tilled = HashSet<Long>()

    fun isTilled(x: Int, y: Int): Boolean = tilled.contains(GameMap.key(x, y))

    fun plant(x: Int, y: Int, day: Int): Boolean {
        if (distanceTo(x, y) > REACH) return false
        if (!isTilled(x, y)) return false
        if (crops.containsKey(GameMap.key(x, y))) return false
        if ((inventory[Item.SEED] ?: 0) <= 0) return false
        inventory[Item.SEED] = (inventory[Item.SEED] ?: 0) - 1
        crops[GameMap.key(x, y)] = Crop(plantedDay = day)
        return true
    }

    /** Watering is once per day and is what actually grows the crop. */
    fun water(x: Int, y: Int): Boolean {
        if (distanceTo(x, y) > REACH) return false
        val crop = crops[GameMap.key(x, y)] ?: return false
        if (crop.wateredToday(waterDay)) return false
        crops[GameMap.key(x, y)] = crop.copy(
            wateredDay = waterDay,
            growth = (crop.growth + 1).coerceAtMost(DAYS_TO_RIPE),
        )
        return true
    }

    /** Set by the caller each real day; two waterings in one day do nothing. */
    var waterDay: Int = 0

    /** Harvest, if ripe: the crop leaves the field and becomes food. */
    fun harvest(x: Int, y: Int, day: Int): Int {
        if (distanceTo(x, y) > REACH) return 0
        val crop = crops[GameMap.key(x, y)] ?: return 0
        if (!crop.isRipe(day)) return 0
        crops.remove(GameMap.key(x, y))
        tilled.remove(GameMap.key(x, y))
        inventory[Item.FOOD] = (inventory[Item.FOOD] ?: 0) + HARVEST_YIELD
        return HARVEST_YIELD
    }

    fun cropAt(x: Int, y: Int): Crop? = crops[GameMap.key(x, y)]

    fun eat(): Boolean {
        if (hunger >= MAX_HUNGER) return false
        if ((inventory[Item.FOOD] ?: 0) <= 0) return false
        inventory[Item.FOOD] = (inventory[Item.FOOD] ?: 0) - 1
        hunger = (hunger + FOOD_VALUE).coerceAtMost(MAX_HUNGER)
        health = (health + 1).coerceAtMost(MAX_HEALTH)
        return true
    }

    // ---------------------------------------------------------------- survival

    /**
     * One tick of survival.
     *
     * Hunger drains with time; when it is empty health drains too. At night,
     * standing in the dark hurts, which is the whole reason to build shelter and
     * light it. Anything lit, or anywhere in daylight, is safe.
     */
    fun tickSurvival(clock: GameClock, minutes: Int = 1): SurvivalTick {
        var starving = false
        var exposed = false

        repeat(minutes.coerceAtLeast(0)) {
            if (hunger > 0) {
                hungerTimer += 1
                if (hungerTimer >= MINUTES_PER_HUNGER) {
                    hungerTimer = 0
                    hunger = (hunger - 1).coerceAtLeast(0)
                }
            } else {
                starving = true
                health = (health - 1).coerceAtLeast(0)
            }

            if (clock.isNight && !isLit(playerX, playerY)) {
                exposed = true
                nightTimer += 1
                if (nightTimer >= MINUTES_PER_NIGHT_DAMAGE) {
                    nightTimer = 0
                    health = (health - 1).coerceAtLeast(0)
                }
            } else {
                nightTimer = 0
            }
        }
        return SurvivalTick(health = health, hunger = hunger, starving = starving, exposedAtNight = exposed)
    }

    private var hungerTimer = 0
    private var nightTimer = 0

    /** Sleep in shelter to skip to morning: Minecraft's bed, Harvest Moon's inn. */
    fun sleep(hasShelter: Boolean): Boolean {
        if (!hasShelter) return false
        health = (health + SLEEP_HEAL).coerceAtMost(MAX_HEALTH)
        hunger = (hunger - 2).coerceAtLeast(0)
        return true
    }

    fun distanceTo(x: Int, y: Int): Int =
        Math.abs(playerX - x) + Math.abs(playerY - y)

    fun addItem(item: Item, count: Int) {
        inventory[item] = (inventory[item] ?: 0) + count
    }

    fun countOf(item: Item): Int = inventory[item] ?: 0

    // ---------------------------------------------------------------- saving

    /** Torches left in the pack; lights already placed are in [lightCells]. */
    val torches: Int get() = inventory[Item.TORCH] ?: 0

    fun lightCells(): Set<Long> = lights.toSet()
    fun clearedCells(): Set<Long> = cleared.toSet()
    fun tilledCells(): Set<Long> = tilled.toSet()
    fun builtCells(): Map<Long, Item> = LinkedHashMap(built)
    fun allCrops(): Map<Long, Crop> = LinkedHashMap(crops)

    /**
     * Puts a loaded save back into this world.
     *
     * Called once, right after construction, so it does not try to be clever
     * about merging: the caller decides whether a save is worth restoring.
     * Player health is never restored to zero (that would be a soft lock) and
     * the light/clear/till sets are copied rather than aliased.
     */
    fun restore(
        playerX: Int,
        playerY: Int,
        facing: Direction,
        health: Int,
        hunger: Int,
        wood: Int,
        stone: Int,
        fibre: Int,
        food: Int,
        seeds: Int,
        torches: Int,
        lightCells: Collection<Long>,
        clearedCells: Collection<Long>,
        tilledCells: Collection<Long>,
        builtCells: Map<Long, Item>,
        crops: Map<Long, Crop>,
    ) {
        if (canStand(playerX, playerY)) {
            this.playerX = playerX
            this.playerY = playerY
        }
        this.facing = facing
        this.health = health.coerceIn(1, MAX_HEALTH)
        this.hunger = hunger.coerceIn(0, MAX_HUNGER)

        inventory[Item.WOOD] = wood.coerceAtLeast(0)
        inventory[Item.STONE] = stone.coerceAtLeast(0)
        inventory[Item.FIBRE] = fibre.coerceAtLeast(0)
        inventory[Item.FOOD] = food.coerceAtLeast(0)
        inventory[Item.SEED] = seeds.coerceAtLeast(0)
        inventory[Item.TORCH] = torches.coerceAtLeast(0)

        lights.clear()
        lights.addAll(lightCells)
        cleared.clear()
        cleared.addAll(clearedCells)
        tilled.clear()
        tilled.addAll(tilledCells)
        built.clear()
        built.putAll(builtCells)
        this.crops.clear()
        this.crops.putAll(crops)
    }

    // ---------------------------------------------------------------- helpers

    private fun dropFor(tileName: String): Item? = when {
        tileName.startsWith("tree") || tileName == "bush" || tileName.startsWith("fence") -> Item.WOOD
        tileName == "rock" -> Item.STONE
        tileName.startsWith("flowers") -> Item.FIBRE
        else -> null
    }

    /**
     * A planted crop.
     *
     * `growth` counts watered days, which is the Harvest Moon rule that makes
     * the watering can a daily job rather than decoration: a crop left dry sits
     * still. The map editor never writes crops, so they live only here.
     */
    data class Crop(val plantedDay: Int, val wateredDay: Int = -1, val growth: Int = 0) {
        fun isRipe(today: Int): Boolean = growth >= DAYS_TO_RIPE
        fun wateredToday(today: Int): Boolean = wateredDay == today
        /** 0..DAYS_TO_RIPE, used by the renderer to size the sprout. */
        fun stage(today: Int): Int = growth.coerceAtMost(DAYS_TO_RIPE)
    }

    /** `label` is what the HUD says; keeping it here keeps the text in one place. */
    enum class Item(val isBlock: Boolean, val label: String) {
        WOOD(true, "kayu"),
        STONE(true, "batu"),
        FIBRE(false, "serat"),
        FOOD(false, "makanan"),
        SEED(false, "bibit"),
        TORCH(true, "lampu"),
    }

    sealed interface MineResult {
        data class Mined(val tile: String, val drop: Item?, val x: Int = 0, val y: Int = 0) : MineResult
        data object Nothing : MineResult
        data object TooFar : MineResult
    }

    sealed interface BuildResult {
        data class Built(val item: Item, val x: Int, val y: Int) : BuildResult
        data object NoMaterial : BuildResult
        data object Blocked : BuildResult
        data object NotABlock : BuildResult
    }

    data class SurvivalTick(
        val health: Int,
        val hunger: Int,
        val starving: Boolean,
        val exposedAtNight: Boolean,
    )

    companion object {
        const val MAX_HEALTH = 10
        const val MAX_HUNGER = 10
        const val FOOD_VALUE = 4
        const val SLEEP_HEAL = 4
        const val HARVEST_YIELD = 2
        const val REACH = 1
        const val LIGHT_RADIUS = 4
        const val MINUTES_PER_HUNGER = 25
        const val MINUTES_PER_NIGHT_DAMAGE = 6
        const val DAYS_TO_RIPE = 2
    }
}

enum class Direction(val dx: Int, val dy: Int) {
    UP(0, -1), DOWN(0, 1), LEFT(-1, 0), RIGHT(1, 0);

    companion object {
        fun toward(fromX: Int, fromY: Int, toX: Int, toY: Int): Direction {
            val dx = toX - fromX
            val dy = toY - fromY
            return when {
                Math.abs(dx) >= Math.abs(dy) -> if (dx >= 0) RIGHT else LEFT
                dy >= 0 -> DOWN
                else -> UP
            }
        }
    }
}
