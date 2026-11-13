package dev.retrobit.pokelauncher.game

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The rules of the world, tested without Android.
 *
 * These cover the decisions that are expensive to discover in the app: walking
 * through walls, mining or building out of reach, and starvation or night damage
 * killing the player while they are still "playing".
 */
class WorldTest {

    // ------------------------------------------------------------ a small map

    private val tilesJson = """
        {"tile":16,"columns":8,"tiles":{
          "grass":{"x":0,"y":0,"w":16,"h":16,"solid":false,"layer":"ground"},
          "path":{"x":16,"y":0,"w":16,"h":16,"solid":false,"layer":"ground"},
          "water":{"x":32,"y":0,"w":16,"h":16,"solid":true,"layer":"ground"},
          "tree":{"x":0,"y":16,"w":32,"h":32,"solid":true,"layer":"object"},
          "bush":{"x":32,"y":16,"w":16,"h":16,"solid":true,"layer":"object"},
          "rock":{"x":48,"y":16,"w":16,"h":16,"solid":true,"layer":"object"},
          "flowers_gold":{"x":64,"y":16,"w":16,"h":16,"solid":false,"layer":"object"},
          "fence_h":{"x":0,"y":48,"w":16,"h":16,"solid":true,"layer":"object"}
        }}
    """.trimIndent()

    /**
     * A 10x8 lawn with:
     *  - water down x=5 for rows 0..5, so rows 6..7 are the way around it,
     *  - a tree standing at 2,2 on grass, reachable from 2,3,
     *  - plain grass everywhere else.
     *
     * Built layer by layer into one object per cell, which is the format the
     * editor saves and MapJson reads.
     */
    private fun mapJson(): String {
        val cells = JSONObject()
        for (y in 0 until 8) {
            for (x in 0 until 10) {
                val wet = x == 5 && y <= 5
                cells.put("$x,$y", JSONObject().put("ground", if (wet) "water" else "grass"))
            }
        }
        // the tree sits on top of the grass, it does not replace it
        cells.getJSONObject("2,2").put("object", "tree")
        return JSONObject()
            .put("cols", 10).put("rows", 8)
            .put("cells", cells)
            .toString()
    }

    private fun world(): World {
        val tiles = MapJson.parseTileSet(tilesJson)
        val map = MapJson.parseMap(mapJson(), tiles)
        return World(map, tiles, startX = 2, startY = 3)
    }

    // ---------------------------------------------------------------- parsing

    @Test
    fun `the fixture parses to the map the other tests assume`() {
        // One test states the fixture's contract, so a broken fixture fails here
        // with a readable message instead of failing nine unrelated tests.
        val tiles = MapJson.parseTileSet(tilesJson)
        assertEquals("the test tileset must parse", 8, tiles.tiles.size)

        val json = mapJson()
        val map = MapJson.parseMap(json, tiles)
        assertEquals("10x8 grid expected, json=${json.take(160)}", 10, map.cols)
        assertEquals(8, map.rows)
        assertEquals("2,2 ground, json=${json.take(400)}", "grass", map.cell(2, 2)?.ground)
        assertEquals("2,2 object", "tree", map.cell(2, 2)?.objectTile)
        assertEquals("2,3 must be open grass", false, map.isSolid(2, 3, tiles))
        assertEquals("5,3 must be water", true, map.isSolid(5, 3, tiles))
        assertEquals("5,7 must be open ground so the pond has a bank", false, map.isSolid(5, 7, tiles))
    }

    @Test
    fun `tileset json keeps names, size and collision`() {
        val tiles = MapJson.parseTileSet(tilesJson)
        assertEquals(16, tiles.tile)
        assertEquals(8, tiles.columns)
        assertTrue(tiles["water"]!!.solid)
        assertFalse(tiles["grass"]!!.solid)
        assertEquals(2, tiles["tree"]!!.cellsWide)
        assertEquals(2, tiles["tree"]!!.cellsTall)
    }

    @Test
    fun `a tileset with the wrong tile size is rejected`() {
        val broken = tilesJson.replace("\"tile\":16", "\"tile\":32")
        val failed = runCatching { MapJson.parseTileSet(broken) }.isFailure
        assertTrue("32px tiles must not load into a 16px engine", failed)
    }

    @Test
    fun `a map with no size is rejected`() {
        val failed = runCatching {
            MapJson.parseMap("""{"cells":{}}""", MapJson.parseTileSet(tilesJson))
        }.isFailure
        assertTrue(failed)
    }

    @Test
    fun `cells outside the grid are dropped, not trusted`() {
        val tiles = MapJson.parseTileSet(tilesJson)
        val json = JSONObject(mapJson()).apply {
            getJSONObject("cells").put("99,99", JSONObject().put("name", "grass").put("layer", "ground"))
        }.toString()
        val map = MapJson.parseMap(json, tiles)
        assertNull(map.cell(99, 99))
    }

    @Test
    fun `unknown tile names are dropped so a renamed tile cannot crash a map`() {
        val tiles = MapJson.parseTileSet(tilesJson)
        val json = JSONObject(mapJson()).apply {
            getJSONObject("cells").put("3,3", JSONObject().put("object", "no_such_tile"))
        }.toString()
        val map = MapJson.parseMap(json, tiles)
        assertNull(map.cell(3, 3)?.objectTile)
        assertEquals("the ground must survive a bad object layer", "grass", map.cell(3, 3)?.ground)
    }

    @Test
    fun `an old single-name map still loads`() {
        val tiles = MapJson.parseTileSet(tilesJson)
        val json = JSONObject()
            .put("cols", 3).put("rows", 2)
            .put("cells", JSONObject().put("1,1", JSONObject().put("name", "tree").put("layer", "object")))
            .toString()
        val map = MapJson.parseMap(json, tiles)
        assertEquals("tree", map.cell(1, 1)?.objectTile)
    }

    @Test
    fun `ground and object share a cell`() {
        val tiles = MapJson.parseTileSet(tilesJson)
        // the tree at 2,2 sits on grass: both must survive the merge
        val map = MapJson.parseMap(mapJson(), tiles)
        assertEquals("grass", map.cell(2, 2)?.ground)
        assertEquals("tree", map.cell(2, 2)?.objectTile)
    }

    // ---------------------------------------------------------------- walking

    @Test
    fun `walking into water is blocked and keeps the player in place`() {
        val world = world()
        // stand left of the water strip
        world.step(Direction.RIGHT) // 3,3
        world.step(Direction.RIGHT) // 4,3
        val moved = world.step(Direction.RIGHT) // 5,3 is water
        assertFalse(moved)
        assertEquals(4, world.playerX)
        assertEquals(3, world.playerY)
    }

    @Test
    fun `walking into a tree is blocked`() {
        val world = world()
        // the tree stands at 2,2 and the player at 2,3: one step up is refused
        val moved = world.step(Direction.UP)
        assertFalse(moved)
        assertEquals(2, world.playerX)
        assertEquals(3, world.playerY)
    }

    @Test
    fun `turning works even when the step is blocked`() {
        val world = world()
        world.step(Direction.LEFT) // 1,3 then keep turning left at the edge
        repeat(3) { world.step(Direction.LEFT) }
        assertEquals(Direction.LEFT, world.facing)
    }

    @Test
    fun `the map edge cannot be walked off`() {
        val world = world()
        repeat(20) { world.step(Direction.LEFT) }
        repeat(20) { world.step(Direction.UP) }
        assertTrue(world.playerX >= 0)
        assertTrue(world.playerY >= 0)
    }

    // ---------------------------------------------------------------- building

    @Test
    fun `mining a tree yields wood and clears the cell`() {
        // Start away from the tree so reach is actually exercised: the spawn is
        // 2,3 and the tree 2,2, so from there the tree is already adjacent.
        val world = World(MapJson.parseMap(mapJson(), MapJson.parseTileSet(tilesJson)),
            MapJson.parseTileSet(tilesJson), startX = 8, startY = 7)

        // 2,3 is plain grass: there is nothing to mine there
        assertTrue(world.mine(2, 3) is World.MineResult.Nothing)

        val far = world.mine(2, 2)
        assertTrue("a tree six cells away is out of reach", far is World.MineResult.TooFar)

        // Walk to the tree. The pond at x=5 blocks row 2, so go up to row 6
        // (below the pond's last row), cross to x=2, then north.
        world.step(Direction.UP)                      // 8,7 -> 8,6
        assertEquals(6, world.playerY)
        repeat(6) { world.step(Direction.LEFT) }      // 8,6 -> 2,6
        assertEquals(2, world.playerX)
        repeat(3) { world.step(Direction.UP) }        // 2,6 -> 2,3
        assertEquals(3, world.playerY)
        assertTrue("standing next to the tree now", world.mine(2, 2) is World.MineResult.Mined)

        val near = World(MapJson.parseMap(mapJson(), MapJson.parseTileSet(tilesJson)),
            MapJson.parseTileSet(tilesJson), startX = 2, startY = 3)
        val before = near.wood
        val mined = near.mine(2, 2)
        assertTrue("adjacent tree must be minable", mined is World.MineResult.Mined)
        assertEquals(before + 1, near.wood)
        assertFalse("a mined cell is a hole, not a shortcut", near.canStand(2, 2))
    }

    @Test
    fun `mining water does nothing`() {
        val world = world()
        world.step(Direction.RIGHT)
        world.step(Direction.RIGHT)
        val result = world.mine(5, 3)
        assertTrue(result is World.MineResult.Nothing)
    }

    @Test
    fun `building spends material and blocks the cell`() {
        val world = world()
        world.addItem(World.Item.STONE, 2)
        val before = world.countOf(World.Item.STONE)
        val built = world.build(World.Item.STONE)
        assertTrue(built is World.BuildResult.Built)
        assertEquals(before - 1, world.countOf(World.Item.STONE))
        val spot = built as World.BuildResult.Built
        assertEquals(World.Item.STONE, world.builtAt(spot.x, spot.y))
    }

    @Test
    fun `building without material is refused`() {
        val world = world()
        val built = world.build(World.Item.TORCH) // none in the starting kit
        assertTrue(built is World.BuildResult.NoMaterial)
    }

    @Test
    fun `food cannot be placed as a block`() {
        val world = world()
        val built = world.build(World.Item.FOOD)
        assertTrue(built is World.BuildResult.NotABlock)
    }

    // ---------------------------------------------------------------- light

    @Test
    fun `a placed light makes nearby cells safe at night`() {
        val world = world()
        world.addItem(World.Item.TORCH, 1)
        assertFalse(world.isLit(world.playerX, world.playerY))
        assertTrue(world.placeLight())
        assertTrue(world.isLit(world.playerX, world.playerY))
        assertTrue(world.isLit(world.playerX + 2, world.playerY + 2))
        assertFalse(world.isLit(world.playerX + 20, world.playerY))
    }

    // ---------------------------------------------------------------- survival

    @Test
    fun `daytime ticks are harmless`() {
        val world = world()
        val tick = world.tickSurvival(GameClock.atMinute(12 * 60), minutes = 30)
        assertEquals(World.MAX_HEALTH, tick.health)
        assertFalse(tick.exposedAtNight)
    }

    @Test
    fun `night in the dark hurts, night beside a light does not`() {
        val dark = world()
        val cold = dark.tickSurvival(GameClock.atMinute(23 * 60), minutes = 12)
        assertTrue(cold.exposedAtNight)
        assertTrue("12 minutes of night must cost health", cold.health < World.MAX_HEALTH)

        val lit = world()
        lit.addItem(World.Item.TORCH, 1)
        lit.placeLight()
        val warm = lit.tickSurvival(GameClock.atMinute(23 * 60), minutes = 12)
        assertFalse(warm.exposedAtNight)
        assertEquals(World.MAX_HEALTH, warm.health)
    }

    @Test
    fun `hunger drains with time and food restores it`() {
        val world = world()
        world.tickSurvival(GameClock.atMinute(12 * 60), minutes = World.MINUTES_PER_HUNGER * 3)
        assertTrue("three hunger steps must show", world.hunger < World.MAX_HUNGER)
        val fed = world.hunger
        assertTrue(world.eat())
        assertTrue(world.hunger > fed)
    }

    @Test
    fun `eating when full is refused so food is not wasted`() {
        val world = world()
        assertFalse(world.eat())
    }

    @Test
    fun `sleep heals only in shelter`() {
        val world = world()
        world.tickSurvival(GameClock.atMinute(23 * 60), minutes = 20)
        val hurt = world.health
        assertFalse(world.sleep(hasShelter = false))
        assertEquals(hurt, world.health)
        assertTrue(world.sleep(hasShelter = true))
        assertTrue(world.health > hurt)
    }

    // ---------------------------------------------------------------- farming

    @Test
    fun `tilling only works on open grass`() {
        val world = world()
        assertTrue("the cell under the player is open grass", world.till(world.playerX, world.playerY))
        assertFalse("water cannot be tilled", world.till(5, 3))
        assertFalse("a tree cannot be tilled", world.till(2, 2))
    }

    @Test
    fun `a crop needs tilled soil, a seed, and days to ripen`() {
        val world = world()
        val x = world.playerX
        val y = world.playerY
        assertFalse("no soil yet", world.plant(x, y, day = 0))
        world.till(x, y)
        val seeds = world.seeds
        assertTrue(world.plant(x, y, day = 0))
        assertEquals(seeds - 1, world.seeds)
        assertFalse("not ripe the same day", world.cropAt(x, y)!!.isRipe(0))
        assertTrue(world.cropAt(x, y)!!.isRipe(World.DAYS_TO_RIPE))
    }

    @Test
    fun `harvesting ripe crops yields food and clears the field`() {
        val world = world()
        val x = world.playerX
        val y = world.playerY
        world.till(x, y)
        world.plant(x, y, day = 0)
        assertEquals("unripe crops cannot be harvested", 0, world.harvest(x, y, day = 0))
        val food = world.food
        val yield = world.harvest(x, y, day = World.DAYS_TO_RIPE)
        assertTrue(yield > 0)
        assertEquals(food + yield, world.food)
        assertNull(world.cropAt(x, y))
    }

    @Test
    fun `watering counts once per day`() {
        val world = world()
        world.till(world.playerX, world.playerY)
        world.plant(world.playerX, world.playerY, day = 0)
        world.waterDay = 5
        assertTrue(world.water(world.playerX, world.playerY))
        assertFalse("a second watering on the same day does nothing", world.water(world.playerX, world.playerY))
        world.waterDay = 6
        assertTrue(world.water(world.playerX, world.playerY))
    }

    // ---------------------------------------------------------------- camera

    @Test
    fun `camera centres on the player and stops at the map edge`() {
        val camera = Camera(viewWidth = 320, viewHeight = 240, mapWidth = 1600, mapHeight = 1600)
        val centred = camera.follow(800, 800)
        assertEquals(800 - 160, centred.x)
        assertEquals(800 - 120, centred.y)

        val atEdge = camera.follow(0, 0)
        assertEquals(0, atEdge.x)
        assertEquals(0, atEdge.y)

        val farEdge = camera.follow(1590, 1590)
        assertEquals(1600 - 320, farEdge.x)
        assertEquals(1600 - 240, farEdge.y)
    }

    @Test
    fun `a map smaller than the window is centred instead of pinned left`() {
        val camera = Camera(viewWidth = 640, viewHeight = 480, mapWidth = 320, mapHeight = 240)
        val centred = camera.follow(10, 10)
        assertEquals((320 - 640) / 2, centred.x)
        assertEquals((240 - 480) / 2, centred.y)
    }

    // ---------------------------------------------------------------- touch

    @Test
    fun `a tap maps to the cell under the finger`() {
        val camera = Camera(x = 160, y = 64, viewWidth = 640, viewHeight = 480, mapWidth = 2560, mapHeight = 1600)
        // 16px cells: touch 40px in from the camera lands on the 2nd cell
        val cell = TouchInput.cellAt(40f, 40f, camera)
        assertEquals(160 / 16 + 2, cell.first)
        assertEquals(64 / 16 + 2, cell.second)
    }

    @Test
    fun `a tap on the player is a self tap, not a walk`() {
        assertTrue(TouchInput.isSelfTap(3 to 4, 3, 4))
        assertFalse(TouchInput.isSelfTap(4 to 4, 3, 4))
    }

    // ---------------------------------------------------------------- pathing

    @Test
    fun `tap to move finds the shortest way around water`() {
        val world = world()
        // from (2,3) to (8,3): the water at x=5 blocks the straight line
        val path = Pathfinder.find(2, 3, 8, 3) { x, y -> world.canStand(x, y) }
        assertTrue("a path around the pond must exist", path.isNotEmpty())
        assertTrue("the path must end on the goal", path.last() == 8 to 3)
        assertTrue("no step in the path may be blocked", path.all { (x, y) -> world.canStand(x, y) })
        assertTrue("the water must be detoured, so the path is longer than 6", path.size > 6)
    }

    @Test
    fun `tapping a solid cell walks to the cell beside it`() {
        val world = world()
        val path = Pathfinder.find(2, 3, 2, 2) { x, y -> world.canStand(x, y) }
        assertTrue("a tree tap must still walk somewhere useful", path.isNotEmpty())
        val (lx, ly) = path.last()
        assertTrue("the walk stops next to the tree, never on it", !(lx == 2 && ly == 2))
        assertTrue(Math.abs(lx - 2) + Math.abs(ly - 2) == 1)
    }

    @Test
    fun `an unreachable goal returns an empty path instead of hanging`() {
        val walls = MapJson.parseTileSet(tilesJson)
        val json = JSONObject()
        json.put("cols", 6).put("rows", 3)
        val cells = JSONObject()
        for (y in 0 until 3) {
            for (x in 0 until 6) {
                val name = if (x == 3) "water" else "grass"
                cells.put("$x,$y", JSONObject().put("name", name).put("layer", "ground"))
            }
        }
        json.put("cells", cells)
        val map = MapJson.parseMap(json.toString(), walls)
        val path = Pathfinder.find(0, 0, 5, 0) { x, y -> !map.isSolid(x, y, walls) }
        assertTrue("a wall from edge to edge cannot be crossed", path.isEmpty())
    }

    // ---------------------------------------------------------------- clock

    @Test
    fun `the clock reads real wall time`() {
        // 2024-01-01T00:00:00Z is 07:00 in Jakarta (UTC+7)
        val clock = GameClock.fromMillisUtc(1_704_067_200_000L, utcOffsetMinutes = 7 * 60)
        assertEquals(7, clock.hour)
        assertEquals(0, clock.minute)
        assertFalse(clock.isNight)
    }

    @Test
    fun `night is the window from 18 to 6`() {
        assertFalse(GameClock.atMinute(5 * 60 + 59).isNight)
        assertTrue(GameClock.atMinute(6 * 60).isNight.not())
        assertTrue(GameClock.atMinute(18 * 60).isNight)
        assertTrue("midnight is night", GameClock.atMinute(0).isNight)
        assertTrue(GameClock.atMinute(23 * 60 + 59).isNight)
    }

    @Test
    fun `daylight peaks at noon and is zero before dawn`() {
        assertEquals(1f, GameClock.atMinute(12 * 60).daylight, 0.001f)
        assertEquals(0f, GameClock.atMinute(2 * 60).daylight, 0.001f)
        assertEquals(0.5f, GameClock.atMinute(5 * 60).daylight, 0.01f)
        assertEquals("the clock wraps at midnight", 0, GameClock.atMinute(24 * 60).minuteOfDay)
    }

    // ---------------------------------------------------------------- assets

    @Test
    fun `the shipped tileset loads and has the tiles the game needs`() {
        // Gradle runs unit tests with app/ as the working directory, so this is
        // the file that ends up inside the APK.
        val path = listOf(
            java.io.File("src/main/assets/tileset/tileset.json"),
            java.io.File("app/src/main/assets/tileset/tileset.json"),
        ).firstOrNull { it.exists() }
        assertNotNull("tileset.json must be packaged in the app", path)
        val tiles = MapJson.parseTileSet(path!!.readText())
        assertEquals(16, tiles.tile)
        for (name in listOf("grass", "path", "water", "tree", "roof", "wall_door",
                            "machine_left", "machine_right")) {
            assertNotNull("missing tile: $name", tiles[name])
        }
    }

    @Test
    fun `the shipped starter map is playable`() {
        val dir = listOf("src/main/assets/tileset", "app/src/main/assets/tileset")
            .map { java.io.File(it) }
            .firstOrNull { it.resolve("map.json").exists() }
        assertNotNull("map.json must be packaged in the app", dir)
        val tiles = MapJson.parseTileSet(dir!!.resolve("tileset.json").readText())
        val map = MapJson.parseMap(dir.resolve("map.json").readText(), tiles)

        assertTrue("the starter map should be big enough to explore",
            map.cols >= 40 && map.rows >= 25)
        assertFalse("the spawn must not be inside a wall", map.isSolid(map.spawnX, map.spawnY, tiles))

        // every cell the map mentions must use a tile that exists
        var placed = 0
        for ((x, y, cell) in map.entries()) {
            placed++
            for (name in listOfNotNull(cell.ground, cell.building, cell.objectTile)) {
                assertNotNull("unknown tile '$name' at $x,$y", tiles[name])
            }
        }
        assertTrue("the map should have cells", placed > 0)
    }
}
