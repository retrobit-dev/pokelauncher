package dev.retrobit.pokelauncher.game

/**
 * The tile atlas as the game sees it: a lookup from tile name to a rectangle
 * on one sheet, plus whether that tile blocks movement.
 *
 * Mirrors `docs/tileset/tileset.json`, which `tools/tileset/build.py` writes and
 * the map editor reads. Keeping the same names in all three places is what lets
 * a map painted in the browser load unchanged in the app.
 */
data class TileSet(
    val tile: Int,
    val columns: Int,
    val tiles: Map<String, Tile>,
) {
    data class Tile(
        val name: String,
        val x: Int,
        val y: Int,
        val w: Int,
        val h: Int,
        val solid: Boolean,
        val layer: String,
    ) {
        /** Tiles are 16x16 except the 2x2 tree, so footprints are in cells. */
        val cellsWide: Int get() = w / 16
        val cellsTall: Int get() = h / 16
    }

    operator fun get(name: String): Tile? = tiles[name]

    /** A tile nobody indexed must not crash the renderer. */
    fun orGrass(name: String): Tile? = tiles[name] ?: tiles["grass"]
}

/**
 * One cell of the map. Ground, object and building each get their own tile so a
 * tree can stand on a path.
 *
 * `null` means "nothing here", and is deliberately distinct from `""`: an
 * erased cell is absent, not named.
 */
data class Cell(
    val ground: String? = null,
    val objectTile: String? = null,
    val building: String? = null,
) {
    val isEmpty: Boolean get() = ground == null && objectTile == null && building == null
}

/**
 * A map is a fixed grid of cells plus a spawn point.
 *
 * The editor writes 160x100 for the MatePad Mini panel (2560x1600 at 16px), but
 * nothing here assumes that size: a smaller test map is just as valid.
 */
class GameMap(
    val cols: Int,
    val rows: Int,
    private val cells: Map<Long, Cell>,
    val spawnX: Int = cols / 2,
    val spawnY: Int = rows / 2,
) {
    val widthPx: Int get() = cols * TILE
    val heightPx: Int get() = rows * TILE

    fun inBounds(x: Int, y: Int): Boolean = x in 0 until cols && y in 0 until rows

    fun cell(x: Int, y: Int): Cell? = cells[key(x, y)]

    /** All placed cells, for the renderer. */
    fun entries(): Sequence<Triple<Int, Int, Cell>> = cells.entries.asSequence()
        .map { (k, cell) -> Triple((k shr 32).toInt(), (k and 0xFFFFFFFFL).toInt(), cell) }

    /**
     * Collision asks about the tile that actually stops you: an object first,
     * then a building, then the ground. Water is ground but still blocks.
     */
    fun isSolid(x: Int, y: Int, tiles: TileSet): Boolean {
        if (!inBounds(x, y)) return true
        val cell = cells[key(x, y)] ?: return false
        for (name in listOf(cell.objectTile, cell.building, cell.ground)) {
            if (name == null) continue
            val tile = tiles[name] ?: continue
            if (tile.solid) return true
        }
        return false
    }

    companion object {
        const val TILE = 16

        fun key(x: Int, y: Int): Long = (x.toLong() shl 32) or (y.toLong() and 0xFFFFFFFFL)

        fun fromCells(
            cols: Int,
            rows: Int,
            cells: Map<Long, Cell>,
            spawnX: Int = cols / 2,
            spawnY: Int = rows / 2,
        ): GameMap {
            // Drop anything outside the grid instead of trusting the file.
            val kept = cells.filterKeys { (k) ->
                val x = (k shr 32).toInt()
                val y = (k and 0xFFFFFFFFL).toInt()
                x in 0 until cols && y in 0 until rows
            }
            return GameMap(cols, rows, kept, spawnX, spawnY)
        }
    }
}
