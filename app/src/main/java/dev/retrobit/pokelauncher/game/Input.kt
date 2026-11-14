package dev.retrobit.pokelauncher.game

/**
 * Turns a finger position into a cell.
 *
 * All the touch maths lives here, away from Compose, for one reason: an
 * off-by-one in this function makes the game feel broken ("I tapped the tree and
 * nothing happened") and is invisible in a screenshot. It is much easier to test
 * as arithmetic than as a gesture handler.
 */
object TouchInput {

    /**
     * Converts a touch point to a map cell.
     *
     * @param touchX pixel x inside the game view
     * @param touchY pixel y inside the game view
     * @param camera what the view is currently showing
     */
    fun cellAt(touchX: Float, touchY: Float, camera: Camera): Pair<Int, Int> {
        val worldX = camera.x + touchX.toInt()
        val worldY = camera.y + touchY.toInt()
        return Math.floorDiv(worldX, GameMap.TILE) to Math.floorDiv(worldY, GameMap.TILE)
    }

    /**
     * A tap on the player themselves is a "use" (till, plant, eat), not a walk.
     * Kept as its own rule because it is the one gesture that looks identical to
     * moving and must not start a path.
     */
    fun isSelfTap(cell: Pair<Int, Int>, playerX: Int, playerY: Int): Boolean =
        cell.first == playerX && cell.second == playerY

    /**
     * Touch zoom: the editor and the game share integer scale steps so the
     * pixels never smear. Pinching in the game is a convenience, not a core
     * control; the steps stay on whole multiples of 16.
     */
    fun zoomStep(current: Int, pinchFactor: Float, steps: IntArray = STEPS): Int {
        if (pinchFactor > 1.25f) return steps.firstOrNull { it > current } ?: current
        if (pinchFactor < 0.8f) return steps.lastOrNull { it < current } ?: current
        return current
    }

    /**
     * Zoom levels, all whole multiples so a tile stays an exact pixel count.
     *
     * 8 and 12 exist for the tablet panel: at 8x a cell is 128 px and the
     * player 128 px tall, at 12x they are 192 px. The default lives on this
     * list, and `defaultStep()` asserts that at startup: a default that is not
     * a step used to break zoom-out entirely (indexOf returned -1, which is
     * why the old code coerced it to 0).
     */
    val STEPS = intArrayOf(1, 2, 3, 4, 6, 8, 10, 12)

    /** Index of the default zoom, or an error naming the mismatch. */
    fun defaultIndex(default: Int = DEFAULT): Int {
        val index = STEPS.indexOf(default)
        require(index >= 0) { "zoom default $default is not one of ${STEPS.toList()}" }
        return index
    }

    /**
     * The zoom the app opens at: 10x.
     *
     * 16x10 cells visible, a 160 px player (10% of the panel height). 12x was
     * tried first and is too close: the road alone filled a third of the
     * screen and there was nothing left to read around the player.
     */
    const val DEFAULT = 10
}
