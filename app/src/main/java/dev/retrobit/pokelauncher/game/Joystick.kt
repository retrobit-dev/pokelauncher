package dev.retrobit.pokelauncher.game

/**
 * Turns a finger on the on-screen pad into a direction.
 *
 * Plain object, no Android import: the pad's whole job is "where did the thumb
 * go", and that is the part worth testing on the JVM. The Compose layer only
 * draws the disc and forwards the touch offset.
 *
 * The pad is a disc with a dead zone in the middle. A dead zone matters on a
 * tablet: the thumb rests near the centre, and without it a resting finger
 * would walk the player into a wall and keep pushing.
 */
object Joystick {

    /** Radius of the drawn disc, in device independent pixels. */
    const val RADIUS_DP = 76f

    /** Radius of the knob that follows the thumb. */
    const val KNOB_DP = 30f

    /**
     * How far from the centre the thumb must travel before it counts, as a
     * fraction of [RADIUS_DP]. A fifth of the disc: 15 dp on a 76 dp pad, which
     * is bigger than the wobble of a thumb resting on glass.
     */
    const val DEAD_ZONE = 0.2f

    /**
     * The direction a thumb at ([dx], [dy]) from the pad centre asks for, or
     * null when it is inside the dead zone.
     *
     * Screen coordinates: y grows downwards, so a negative [dy] means up.
     * The axis with the larger travel wins, which makes the pad feel like four
     * buttons without ever being ambiguous: a diagonal resolves to whichever
     * way the thumb went further.
     */
    fun direction(dx: Float, dy: Float, radius: Float = RADIUS_DP): Direction? {
        if (radius <= 0f) return null
        val distance = kotlin.math.sqrt(dx * dx + dy * dy)
        if (distance / radius < DEAD_ZONE) return null
        val ax = kotlin.math.abs(dx)
        val ay = kotlin.math.abs(dy)
        // Horizontal wins its own tie: an exact diagonal is not a rare edge case
        // on a pad made of pixels, and `>` alone sent (30, 30) down instead of
        // right, because the vertical branch was also the else branch. That is
        // the kind of bug that feels like the player stuttering.
        return if (ax >= ay) {
            if (dx > 0f) Direction.RIGHT else Direction.LEFT
        } else {
            if (dy > 0f) Direction.DOWN else Direction.UP
        }
    }

    /**
     * Where the knob sits for a thumb at ([dx], [dy]), clamped to the disc.
     *
     * The knob is feedback, not input: it stops at the rim so it never suggests
     * travel the pad cannot ask for.
     */
    fun knob(dx: Float, dy: Float, radius: Float = RADIUS_DP): Pair<Float, Float> {
        if (radius <= 0f) return 0f to 0f
        val distance = kotlin.math.sqrt(dx * dx + dy * dy)
        // A thumb exactly at the centre has no direction to be scaled in; the
        // scale factor would be radius/0. This is not theoretical: it is the
        // resting state, and the test that caught it starts there.
        if (distance <= radius || distance == 0f) return dx to dy
        val k = radius / distance
        return dx * k to dy * k
    }
}
