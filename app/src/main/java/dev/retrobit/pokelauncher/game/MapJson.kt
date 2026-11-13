package dev.retrobit.pokelauncher.game

import org.json.JSONException
import org.json.JSONObject

/**
 * Reads the two files the browser tools produce.
 *
 * Both are small JSON documents whose shape is owned by the Python and
 * JavaScript side:
 *
 *  - `tileset.json` from `tools/tileset/build.py`
 *  - `map.json` from the editor (`POST /api/map`, saved as `docs/tileset/map.json`)
 *
 * Parsing is kept strict about the things that would silently corrupt a map
 * (a missing tile size, cells that point at tiles that do not exist) and
 * forgiving about the rest, so a slightly newer file from the editor still
 * loads instead of crashing the home screen.
 */
object MapJson {

    class ParseException(message: String) : Exception(message)

    fun parseTileSet(json: String): TileSet {
        val root = try {
            JSONObject(json)
        } catch (error: JSONException) {
            throw ParseException("tileset.json tidak valid: ${error.message}")
        }

        val tile = root.optInt("tile", 0)
        if (tile != GameMap.TILE) {
            throw ParseException("ukuran tile harus 16 px, bukan $tile")
        }

        val raw = root.optJSONObject("tiles") ?: throw ParseException("tileset.json tanpa 'tiles'")
        val tiles = LinkedHashMap<String, TileSet.Tile>()
        for (name in raw.keys()) {
            val entry = raw.optJSONObject(name) ?: continue
            val w = entry.optInt("w", 0)
            val h = entry.optInt("h", 0)
            if (w <= 0 || h <= 0) continue
            tiles[name] = TileSet.Tile(
                name = name,
                x = entry.optInt("x", 0),
                y = entry.optInt("y", 0),
                w = w,
                h = h,
                solid = entry.optBoolean("solid", false),
                layer = entry.optString("layer", "object"),
            )
        }
        if (tiles.isEmpty()) throw ParseException("tileset.json tidak berisi tile apa pun")

        return TileSet(tile = tile, columns = root.optInt("columns", 8), tiles = tiles)
    }

    /**
     * The editor saves `cells` as an object keyed `"x,y"` with the tile name and
     * its layer. Unknown tile names are dropped: that is how a map survives a
     * tile being renamed in the atlas.
     */
    fun parseMap(json: String, tiles: TileSet): GameMap {
        val root = try {
            JSONObject(json)
        } catch (error: JSONException) {
            throw ParseException("map.json tidak valid: ${error.message}")
        }

        val cols = root.optInt("cols", 0)
        val rows = root.optInt("rows", 0)
        if (cols <= 0 || rows <= 0) throw ParseException("peta tanpa ukuran cols/rows")
        if (cols > MAX_SIDE || rows > MAX_SIDE) {
            throw ParseException("peta $cols x $rows terlalu besar")
        }

        val raw = root.optJSONObject("cells") ?: JSONObject()
        val cells = HashMap<Long, Cell>(raw.length() * 2)
        for (rawKey in raw.keys()) {
            val value = raw.optJSONObject(rawKey) ?: continue
            val coords = rawKey.split(',')
            if (coords.size != 2) continue
            val x = coords[0].trim().toIntOrNull() ?: continue
            val y = coords[1].trim().toIntOrNull() ?: continue
            if (x !in 0 until cols || y !in 0 until rows) continue
            val k = GameMap.key(x, y)

            // Current format: {"ground":"grass","object":"tree"}. A cell holds one
            // tile per layer, which is why a tree has lawn under it instead of a
            // hole. Older files stored a single {"name":..,"layer":..}; both load.
            val known = value.keys().asSequence()
                .filter { it == "ground" || it == "building" || it == "object" }
                .count()
            if (known > 0) {
                var cell = cells[k] ?: Cell()
                for (layer in listOf("ground", "building", "object")) {
                    val name = value.optString(layer, "")
                    if (name.isEmpty() || tiles[name] == null) continue
                    cell = when (layer) {
                        "ground" -> cell.copy(ground = name)
                        "building" -> cell.copy(building = name)
                        else -> cell.copy(objectTile = name)
                    }
                }
                if (!cell.isEmpty) cells[k] = cell
                continue
            }

            val name = value.optString("name", "")
            if (name.isEmpty() || tiles[name] == null) continue
            val layer = value.optString("layer", tiles[name]?.layer ?: "object")
            val existing = cells[k] ?: Cell()
            cells[k] = when (layer) {
                "ground" -> existing.copy(ground = name)
                "building" -> existing.copy(building = name)
                else -> existing.copy(objectTile = name)
            }
        }

        // Spawn is optional in the file: the middle of the map is a fine default.
        val spawn = root.optJSONObject("spawn")
        val spawnX = spawn?.optInt("x", cols / 2)?.coerceIn(0, cols - 1) ?: (cols / 2)
        val spawnY = spawn?.optInt("y", rows / 2)?.coerceIn(0, rows - 1) ?: (rows / 2)

        return GameMap.fromCells(cols, rows, cells, spawnX, spawnY)
    }

    /** Row-major grid the game can walk, used by tests and by the renderer. */
    fun parseLayout(json: String, tiles: TileSet): List<List<String?>> {
        val map = parseMap(json, tiles)
        return (0 until map.rows).map { y ->
            (0 until map.cols).map { x -> map.cell(x, y)?.ground }
        }
    }

    const val MAX_SIDE = 512
}
