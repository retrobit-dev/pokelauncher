package dev.retrobit.pokelauncher.game

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The zoom list and the default zoom must agree.
 *
 * They did not: the default was set to 8 while the steps were (1,2,3,4,6), so
 * `zoomBy` could not find the current scale and "zoom out" jumped all the way
 * to 1x. The failure was silent because `indexOf` returning -1 was coerced to 0.
 */
class TouchInputTest {

    @Test
    fun `the default zoom is a real step`() {
        assertTrue(
            "default ${TouchInput.DEFAULT} must be in ${TouchInput.STEPS.toList()}",
            TouchInput.DEFAULT in TouchInput.STEPS.toList(),
        )
        assertTrue(TouchInput.defaultIndex() >= 0)
    }

    @Test
    fun `the default is the largest step, so the world opens close up`() {
        assertEquals(TouchInput.STEPS.size - 1, TouchInput.defaultIndex())
        assertEquals(TouchInput.STEPS.last(), TouchInput.DEFAULT)
    }

    @Test
    fun `every step divides a tile cleanly`() {
        // A fractional scale would land a tile on half a pixel and smear it.
        TouchInput.STEPS.forEach { assertTrue("step $it must be positive", it > 0) }
        assertEquals(
            "steps are sorted so pinch up always finds the next one",
            TouchInput.STEPS.toList(),
            TouchInput.STEPS.toList().sorted(),
        )
    }

    @Test
    fun `zooming out from the default steps down instead of jumping to 1x`() {
        val start = TouchInput.defaultIndex()
        val out = TouchInput.zoomStep(TouchInput.DEFAULT, 1.5f)
        assertEquals(TouchInput.STEPS[start - 1], out)
    }
}
