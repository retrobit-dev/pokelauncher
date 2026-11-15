package dev.retrobit.pokelauncher.game

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The pad's rules, away from the screen.
 *
 * A thumb on glass wobbles. These tests pin down the two things that make the
 * difference between a pad that feels solid and one that fights the player: a
 * dead zone big enough to rest in, and a diagonal that resolves one way only.
 */
class JoystickTest {

    private val r = 76f

    @Test
    fun `a resting thumb moves nothing`() {
        assertNull("centre", Joystick.direction(0f, 0f, r))
        assertNull("a wobble inside the dead zone", Joystick.direction(6f, -4f, r))
        // 20% of 76 is 15.2, so 14 is still at rest
        assertNull(Joystick.direction(14f, 0f, r))
    }

    @Test
    fun `a thumb past the dead zone walks that way`() {
        assertEquals(Direction.RIGHT, Joystick.direction(r * 0.8f, 0f, r))
        assertEquals(Direction.LEFT, Joystick.direction(-r * 0.8f, 0f, r))
        assertEquals(Direction.UP, Joystick.direction(0f, -r * 0.8f, r))
        assertEquals(Direction.DOWN, Joystick.direction(0f, r * 0.8f, r))
    }

    @Test
    fun `up is the negative y on a screen`() {
        // The one sign error that would silently invert the pad: screen y grows
        // downwards, so pushing up is a negative y.
        assertEquals(Direction.UP, Joystick.direction(0f, -40f, r))
        assertEquals(Direction.DOWN, Joystick.direction(0f, 40f, r))
    }

    @Test
    fun `a diagonal resolves to the axis that moved further`() {
        // Not "the last one wins": a thumb drifting up-right must answer the
        // same way twice in a row, or the player stutters between two cells.
        assertEquals(Direction.RIGHT, Joystick.direction(50f, -20f, r))
        assertEquals(Direction.UP, Joystick.direction(20f, -50f, r))
        assertEquals(Direction.LEFT, Joystick.direction(-40f, 30f, r))
        assertEquals(Direction.DOWN, Joystick.direction(30f, 40f, r))
    }

    @Test
    fun `an exact diagonal still answers one way`() {
        assertEquals(Direction.RIGHT, Joystick.direction(30f, 30f, r))
        assertEquals(Direction.LEFT, Joystick.direction(-30f, 30f, r))
    }

    @Test
    fun `the knob stops at the rim`() {
        val (x, y) = Joystick.knob(400f, 0f, r)
        assertEquals(r, x, 0.01f)
        assertEquals(0f, y, 0.01f)
        // inside the disc the knob simply follows the thumb
        val (ix, iy) = Joystick.knob(10f, -12f, r)
        assertEquals(10f, ix, 0.01f)
        assertEquals(-12f, iy, 0.01f)
    }

    @Test
    fun `a zero radius is handled rather than dividing by it`() {
        assertNull(Joystick.direction(5f, 5f, 0f))
        val (x, y) = Joystick.knob(5f, 5f, 0f)
        assertEquals(0f, x, 0f)
        assertEquals(0f, y, 0f)
    }

    @Test
    fun `the pad is sized like a thumb pad, not a button`() {
        // 76 dp at 160 dpi is about 12 mm across the radius: a thumb pad, not a
        // dot. The numbers are checked here because the mock draws the tablet
        // shot from them (tools/mock_ingame.py) and a silent change would make
        // the picture and the device disagree.
        assertEquals(76f, Joystick.RADIUS_DP, 0f)
        assertEquals(30f, Joystick.KNOB_DP, 0f)
        assertEquals(0.2f, Joystick.DEAD_ZONE, 0.0001f)
        // the knob is smaller than the disc and big enough to find by touch
        assertTrue(Joystick.KNOB_DP < Joystick.RADIUS_DP)
        assertTrue(Joystick.KNOB_DP > 20f)
    }
}
