package dev.retrobit.pokelauncher.game

import org.json.JSONException
import org.json.JSONObject

/**
 * Saves and restores everything the player changed.
 *
 * A launcher is a home screen: Android kills it whenever memory is short, so a
 * world that only lives in RAM loses the field, the fence and the torches every
 * time the process dies. This object turns those changes into one small JSON
 * document and back.
 *
 * Kept out of `World` on purpose. The rules stay a pure state machine, and the
 * file format can grow (more crops, more materials) without touching gameplay.
 * The parser is forgiving: a corrupt or older save must cost the player their
 * field, never the home screen.
 */
object WorldState {

    /** Bumped only when an older file could be misread, not on every addition. */
    const val VERSION = 1

    /**
     * A snapshot of the mutable parts of a world.
     *
     * `key` is [GameMap.key]'s Long, kept as a plain number: unpacking to pairs
     * here would just mean packing them again inside `World`.
     */
    data class Snapshot(
        val playerX: Int,
        val playerY: Int,
        val facing: Direction,
        val health: Int,
        val hunger: Int,
        val wood: Int,
        val stone: Int,
        val fibre: Int,
        val food: Int,
        val seeds: Int,
        val torches: Int,
        val day: Int,
        val lightCells: List<Long>,
        val clearedCells: List<Long>,
        val tilledCells: List<Long>,
        val builtCells: Map<Long, World.Item>,
        val crops: Map<Long, World.Crop>,
    )

    fun snapshot(world: World, day: Int): Snapshot = Snapshot(
        playerX = world.playerX,
        playerY = world.playerY,
        facing = world.facing,
        health = world.health,
        hunger = world.hunger,
        wood = world.wood,
        stone = world.stone,
        fibre = world.fibre,
        food = world.food,
        seeds = world.seeds,
        torches = world.torches,
        day = day,
        lightCells = world.lightCells().toList(),
        clearedCells = world.clearedCells().toList(),
        tilledCells = world.tilledCells().toList(),
        builtCells = world.builtCells(),
        crops = world.allCrops(),
    )

    fun restore(snapshot: Snapshot, world: World) {
        world.restore(
            playerX = snapshot.playerX,
            playerY = snapshot.playerY,
            facing = snapshot.facing,
            health = snapshot.health,
            hunger = snapshot.hunger,
            wood = snapshot.wood,
            stone = snapshot.stone,
            fibre = snapshot.fibre,
            food = snapshot.food,
            seeds = snapshot.seeds,
            torches = snapshot.torches,
            lightCells = snapshot.lightCells,
            clearedCells = snapshot.clearedCells,
            tilledCells = snapshot.tilledCells,
            builtCells = snapshot.builtCells,
            crops = snapshot.crops,
        )
    }

    // ------------------------------------------------------------------ json

    fun toJson(snapshot: Snapshot, nowMillis: Long): String {
        val root = JSONObject()
        root.put("version", VERSION)
        root.put("savedAt", nowMillis)

        val player = JSONObject()
        player.put("x", snapshot.playerX)
        player.put("y", snapshot.playerY)
        player.put("facing", snapshot.facing.name)
        root.put("player", player)

        val vitals = JSONObject()
        vitals.put("health", snapshot.health)
        vitals.put("hunger", snapshot.hunger)
        root.put("vitals", vitals)

        val inventory = JSONObject()
        inventory.put(World.Item.WOOD.name, snapshot.wood)
        inventory.put(World.Item.STONE.name, snapshot.stone)
        inventory.put(World.Item.FIBRE.name, snapshot.fibre)
        inventory.put(World.Item.FOOD.name, snapshot.food)
        inventory.put(World.Item.SEED.name, snapshot.seeds)
        inventory.put(World.Item.TORCH.name, snapshot.torches)
        root.put("inventory", inventory)

        root.put("day", snapshot.day)
        root.put("lights", longs(snapshot.lightCells))
        root.put("cleared", longs(snapshot.clearedCells))
        root.put("tilled", longs(snapshot.tilledCells))

        val built = JSONObject()
        for ((cell, item) in snapshot.builtCells) built.put(cell.toString(), item.name)
        root.put("built", built)

        val crops = JSONObject()
        for ((cell, crop) in snapshot.crops) {
            val entry = JSONObject()
            entry.put("planted", crop.plantedDay)
            entry.put("watered", crop.wateredDay)
            entry.put("growth", crop.growth)
            crops.put(cell.toString(), entry)
        }
        root.put("crops", crops)

        return root.toString()
    }

    /**
     * Rebuilds a snapshot, dropping anything that would put the player inside a
     * wall or spend imaginary materials. Returns null when the file is too
     * broken to trust, and the caller starts a fresh world.
     */
    fun fromJson(json: String, world: World, fallbackDay: Int): Parsed? {
        val root = try {
            JSONObject(json)
        } catch (error: JSONException) {
            return null
        }

        val player = root.optJSONObject("player")
        val x = player?.optInt("x", world.playerX) ?: world.playerX
        val y = player?.optInt("y", world.playerY) ?: world.playerY
        if (!world.map.inBounds(x, y)) return null

        val facing = runCatching {
            Direction.valueOf(player?.optString("facing", "DOWN") ?: "DOWN")
        }.getOrDefault(Direction.DOWN)

        val vitals = root.optJSONObject("vitals")
        val inventory = root.optJSONObject("inventory")

        fun count(item: World.Item): Int =
            (inventory?.optInt(item.name, 0) ?: 0).coerceIn(0, MAX_STACK)

        val built = LinkedHashMap<Long, World.Item>()
        root.optJSONObject("built")?.let { raw ->
            for (key in raw.keys()) {
                val cell = key.toLongOrNull() ?: continue
                val item = runCatching { World.Item.valueOf(raw.optString(key, "")) }.getOrNull()
                if (item != null && item.isBlock) built[cell] = item
            }
        }

        val crops = LinkedHashMap<Long, World.Crop>()
        root.optJSONObject("crops")?.let { raw ->
            for (key in raw.keys()) {
                val cell = key.toLongOrNull() ?: continue
                val entry = raw.optJSONObject(key) ?: continue
                crops[cell] = World.Crop(
                    plantedDay = entry.optInt("planted", fallbackDay),
                    wateredDay = entry.optInt("watered", -1),
                    growth = entry.optInt("growth", 0).coerceIn(0, World.DAYS_TO_RIPE),
                )
            }
        }

        return Parsed(
            snapshot = Snapshot(
                playerX = x,
                playerY = y,
                facing = facing,
                health = (vitals?.optInt("health", World.MAX_HEALTH) ?: World.MAX_HEALTH)
                    .coerceIn(1, World.MAX_HEALTH),
                hunger = (vitals?.optInt("hunger", World.MAX_HUNGER) ?: World.MAX_HUNGER)
                    .coerceIn(0, World.MAX_HUNGER),
                wood = count(World.Item.WOOD),
                stone = count(World.Item.STONE),
                fibre = count(World.Item.FIBRE),
                food = count(World.Item.FOOD),
                seeds = count(World.Item.SEED),
                torches = count(World.Item.TORCH),
                day = root.optInt("day", fallbackDay),
                lightCells = parseLongs(root.optJSONArray("lights")),
                clearedCells = parseLongs(root.optJSONArray("cleared")),
                tilledCells = parseLongs(root.optJSONArray("tilled")),
                builtCells = built,
                crops = crops,
            ),
            savedAt = root.optLong("savedAt", 0L),
        )
    }

    data class Parsed(val snapshot: Snapshot, val savedAt: Long)

    /** Caps a hostile file: a save can describe a big field, not a million. */
    private const val MAX_STACK = 9999

    private fun longs(cells: List<Long>): org.json.JSONArray {
        val array = org.json.JSONArray()
        for (cell in cells) array.put(cell)
        return array
    }

    private fun parseLongs(array: org.json.JSONArray?): List<Long> {
        if (array == null) return emptyList()
        val out = ArrayList<Long>(array.length())
        for (index in 0 until array.length()) {
            val value = array.optLong(index, Long.MIN_VALUE)
            if (value != Long.MIN_VALUE) out.add(value)
        }
        return out
    }
}
