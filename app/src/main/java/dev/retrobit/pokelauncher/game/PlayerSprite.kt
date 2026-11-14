package dev.retrobit.pokelauncher.game

/**
 * Which frame of the walk sheet a direction and a step pair up to.
 *
 * The sheet is four rows, one per direction, in the same order as
 * [Direction.ordinal] (up, down, left, right), and two columns of walk frames.
 * The art is 32x32, two map cells each way, so a frame is drawn at twice the
 * tile size and still lands on whole pixels.
 *
 * Left is not drawn: it is the mirror of right. One drawn direction cannot
 * drift out of sync with the other the way a second hand drawn copy would.
 *
 * This is the part worth testing, so it is a plain object with no Android
 * import: the drawing side only consumes [column] / [row].
 */
object PlayerSprite {

    const val FRAMES = 2

    /**
     * Frame size in pixels. The art is 32x32, so the character is two map cells
     * tall and stands a little wider than one: at 16px the face was four pixels
     * wide on a 2560x1600 panel, which read as a marker rather than a person.
     */
    const val TILE = 32

    /**
     * How many map cells the frame covers. The world is drawn in 16px tiles, so
     * the sprite is drawn at twice the tile size and anchored on the player's
     * feet, not their top-left corner: a 32px sprite drawn from the cell corner
     * would float one cell above the ground.
     */
    const val CELLS = 2

    /** Sheet width and height in pixels, for the atlas bounds check. */
    const val SHEET_WIDTH = FRAMES * TILE
    const val SHEET_HEIGHT = 4 * TILE

    /**
     * Walk cycle column. Frame 0 is standing, frame 1 is mid-step, and it is
     * chosen by the step count rather than by a timer: the sprite then changes
     * exactly when the player moves, and stays still when they do not.
     */
    fun column(walking: Boolean, stepParity: Boolean): Int =
        if (walking && stepParity) 1 else 0

    /** Sheet row for a facing direction; the mirrors share a row. */
    fun row(facing: Direction): Int = when (facing) {
        Direction.UP -> 0
        Direction.DOWN -> 1
        Direction.LEFT -> 2
        Direction.RIGHT -> 3
    }

    /** True when this direction's art is the right-facing art flipped. */
    fun mirrored(facing: Direction): Boolean = facing == Direction.LEFT

    /** Pixel origin of a frame inside the sheet. */
    fun frameX(column: Int): Int = column.coerceIn(0, FRAMES - 1) * TILE

    fun frameY(row: Int): Int = row.coerceIn(0, 3) * TILE
}
