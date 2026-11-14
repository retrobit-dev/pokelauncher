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

    val STEPS = intArrayOf(1, 2, 3, 4, 6)
}
