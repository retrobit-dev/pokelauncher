package dev.retrobit.pokelauncher.game

/**
 * A camera that follows the player smoothly, inside a dead zone.
 *
 * Three things make this feel right on a real tablet, and all three are rules
 * rather than magic numbers hidden in the UI:
 *
 *  1. **Dead zone.** The camera does not chase every step. It sits still while
 *     the player is near the middle, which is what stops the world from sliding
 *     under the thumb at every tap. This is the same trick HeartGold uses.
 *  2. **No jitter.** The camera moves at most [maxStep] map pixels per frame.
 *     When the next step is only one or two pixels away it snaps, because a
 *     one-pixel crawl at 60 fps reads as a shiver, not as motion.
 *  3. **No void.** A camera that centres a player near the map edge would show
 *     empty space outside the map. It clamps instead, and when the map is
 *     smaller than the viewport it centres the whole map.
 *
 * The rig is plain Kotlin on purpose: `advance()` is pure arithmetic, so the
 * feel can be tested on the JVM without an emulator or a frame clock.
 */
class CameraRig(
    viewWidth: Int,
    viewHeight: Int,
    mapWidth: Int,
    mapHeight: Int,
    /** Half-width of the still zone around the centre, in map pixels. */
    val deadZoneX: Int = DEFAULT_DEAD_ZONE_X,
    val deadZoneY: Int = DEFAULT_DEAD_ZONE_Y,
    /** Largest jump allowed between frames, in map pixels. */
    val maxStep: Int = DEFAULT_MAX_STEP,
    startX: Int = 0,
    startY: Int = 0,
) {
    var viewWidth: Int = viewWidth
        private set
    var viewHeight: Int = viewHeight
        private set
    var mapWidth: Int = mapWidth
        private set
    var mapHeight: Int = mapHeight
        private set

    /** Top-left corner of the window, in map pixels. */
    var x: Int = 0
        private set
    var y: Int = 0
        private set

    init {
        jumpTo(startX, startY)
    }

    /** The current window, for the renderer. */
    fun camera(): Camera = Camera(
        x = x,
        y = y,
        viewWidth = viewWidth,
        viewHeight = viewHeight,
        mapWidth = mapWidth,
        mapHeight = mapHeight,
    )

    /**
     * Re-measures the panel. The viewport changes when the tablet is rotated,
     * dived, or zoomed, and a camera that kept the old size would clamp against
     * the wrong bounds.
     */
    fun resize(viewWidth: Int, viewHeight: Int, mapWidth: Int = this.mapWidth, mapHeight: Int = this.mapHeight) {
        this.viewWidth = viewWidth.coerceAtLeast(1)
        this.viewHeight = viewHeight.coerceAtLeast(1)
        this.mapWidth = mapWidth
        this.mapHeight = mapHeight
        clampToMap()
    }

    /**
     * One frame: walk the window toward the player, slowly and without leaving
     * the map. Returns true when the camera actually moved, so the caller can
     * skip a redraw on a still frame.
     */
    fun advance(targetX: Int, targetY: Int): Boolean {
        // The window is allowed to sit anywhere that keeps the player inside
        // the dead zone; the current position is the preferred one. Clamping
        // (rather than comparing distances) is what guarantees it settles: any
        // move would land outside the allowed band, so nothing moves at all.
        val goalX = settle(x, targetX, viewWidth, deadZoneX)
        val goalY = settle(y, targetY, viewHeight, deadZoneY)

        val newX = clampToMap(stepToward(x, goalX, maxStep), viewWidth, mapWidth)
        val newY = clampToMap(stepToward(y, goalY, maxStep), viewHeight, mapHeight)
        if (newX == x && newY == y) return false
        x = newX
        y = newY
        return true
    }

    /**
     * Puts the player dead centre at once: spawn, teleport, first frame.
     *
     * Not `settle`: that keeps the player inside the dead zone but does not
     * centre, which looks off-centre on the first screen of a session.
     */
    fun jumpTo(targetX: Int, targetY: Int) {
        x = clampToMap(targetX - viewWidth / 2, viewWidth, mapWidth)
        y = clampToMap(targetY - viewHeight / 2, viewHeight, mapHeight)
    }

    private fun clampToMap() {
        x = clampToMap(x, viewWidth, mapWidth)
        y = clampToMap(y, viewHeight, mapHeight)
    }

    /**
     * Keeps a window inside the map, and centres a map that is smaller than
     * the window. Centring means a *negative* top-left corner: the renderer
     * then pushes the small map into the middle of the panel, which is why the
     * negative value is correct and a plain clamp to 0 would look wrong.
     */
    private fun clampToMap(value: Int, view: Int, map: Int): Int =
        if (map <= view) (map - view) / 2 else value.coerceIn(0, map - view)

    companion object {
        /**
         * A third of the panel is still, which is roughly what the GBA games
         * used. Expressed in map pixels: the view is in map pixels already.
         */
        const val DEFAULT_DEAD_ZONE_X = 2560 / 6
        const val DEFAULT_DEAD_ZONE_Y = 1600 / 6

        /** ~5 map px at 60 fps: fast enough to catch up, slow enough to read. */
        const val DEFAULT_MAX_STEP = 5

        /** How far the window may be from its target at the end of one frame. */
        internal fun stepToward(current: Int, goal: Int, maxStep: Int): Int {
            val delta = goal - current
            if (delta == 0) return current
            if (Math.abs(delta) <= maxStep) return goal   // snap, do not crawl
            return current + if (delta > 0) maxStep else -maxStep
        }

        /**
         * The nearest window position that keeps the target in the dead zone.
         *
         * The band is "window from target-deadZone down to target-view+deadZone".
         * When the dead zone is wider than the view the band inverts, which is
         * exactly when centring is the only honest answer.
         */
        internal fun settle(current: Int, target: Int, view: Int, deadZone: Int): Int {
            val lowest = target - view + Math.max(0, deadZone)
            val highest = target - Math.max(0, deadZone)
            if (lowest > highest) return target - view / 2
            // Never leave the target off screen: entering the visible area is
            // more important than sitting politely inside the still band.
            val mustSee = (target - view + 1).coerceAtMost(target)
            return current.coerceIn(
                minOf(lowest, mustSee),
                maxOf(highest, target - 1),
            )
        }

        /** Largest valid top-left corner: 0 when the map is smaller than the view. */
        internal fun axisMax(view: Int, map: Int): Int =
            if (map <= view) 0 else map - view
    }
}
