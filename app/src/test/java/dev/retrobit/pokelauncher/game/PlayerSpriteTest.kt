package dev.retrobit.pokelauncher.game

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The sprite sheet is four rows in [Direction.ordinal] order, so the mapping is
 * the one thing that can silently be wrong: a swapped row draws the player
 * walking backwards, which is easy to miss on a still screenshot.
 */
class PlayerSpriteTest {

    @Test
    fun `every direction has its own row`() {
        val rows = Direction.values().map { PlayerSprite.row(it) }
        assertEquals(Direction.values().size, rows.toSet().size)
        rows.forEach { assertTrue(it in 0..3) }
    }

    @Test
    fun `rows follow the enum order the sheet is packed in`() {
        Direction.values().forEach { direction ->
            assertEquals(direction.ordinal, PlayerSprite.row(direction))
        }
    }

    @Test
    fun `only the left frame is mirrored`() {
        assertTrue(PlayerSprite.mirrored(Direction.LEFT))
        assertFalse(PlayerSprite.mirrored(Direction.RIGHT))
        assertFalse(PlayerSprite.mirrored(Direction.UP))
        assertFalse(PlayerSprite.mirrored(Direction.DOWN))
    }

    @Test
    fun `standing still shows the neutral frame`() {
        assertEquals(0, PlayerSprite.column(walking = false, stepParity = false))
        assertEquals(0, PlayerSprite.column(walking = false, stepParity = true))
    }

    @Test
    fun `walking alternates between the two frames`() {
        assertEquals(0, PlayerSprite.column(walking = true, stepParity = false))
        assertEquals(1, PlayerSprite.column(walking = true, stepParity = true))
    }

    @Test
    fun `the frame is two map cells tall`() {
        // The art is 32x32 while a map cell is 16x16. If these two drift apart
        // the sprite is either drawn half size or hangs a cell below the feet.
        assertEquals(32, PlayerSprite.TILE)
        assertEquals(2, PlayerSprite.CELLS)
        assertEquals(GameMap.TILE * PlayerSprite.CELLS, PlayerSprite.TILE)
    }

    @Test
    fun `frames stay inside the sheet`() {
        assertEquals(0, PlayerSprite.frameX(0))
        assertEquals(32, PlayerSprite.frameX(1))
        // a bad index must clamp, never read past the end of the atlas
        assertEquals(32, PlayerSprite.frameX(9))
        assertEquals(0, PlayerSprite.frameX(-3))
        assertEquals(96, PlayerSprite.frameY(3))
        assertEquals(96, PlayerSprite.frameY(9))
        assertEquals(64, PlayerSprite.SHEET_WIDTH)
        assertEquals(128, PlayerSprite.SHEET_HEIGHT)
    }
}
