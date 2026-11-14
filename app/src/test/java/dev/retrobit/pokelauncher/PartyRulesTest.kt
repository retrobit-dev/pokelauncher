package dev.retrobit.pokelauncher

import dev.retrobit.pokelauncher.data.PartyRules
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The party is the only piece of launcher logic with rules worth testing, and
 * [PartyRules] is deliberately free of Android dependencies so it can run on
 * the JVM.
 */
class PartyRulesTest {

    @Test
    fun `party starts empty`() {
        assertEquals(emptyList<String>(), PartyRules.add(emptyList(), ""))
    }

    @Test
    fun `adding a key appends it`() {
        assertEquals(listOf("a.b/c.D"), PartyRules.add(emptyList(), "a.b/c.D"))
    }

    @Test
    fun `adding the same key twice is a no-op`() {
        val party = listOf("a.b/c.D")
        assertEquals(party, PartyRules.add(party, "a.b/c.D"))
    }

    @Test
    fun `party accepts at most six apps`() {
        var party = emptyList<String>()
        repeat(6) { index -> party = PartyRules.add(party, "pkg$index/Activity") }
        assertEquals(6, party.size)
        assertTrue(PartyRules.isFull(party))

        val seventh = PartyRules.add(party, "pkg6/Activity")
        assertEquals(6, seventh.size)
        assertFalse(seventh.contains("pkg6/Activity"))
    }

    @Test
    fun `removing a missing key keeps the party`() {
        val party = listOf("a.b/c.D")
        assertEquals(party, PartyRules.remove(party, "x.y/z.W"))
    }

    @Test
    fun `toggle adds then removes`() {
        val added = PartyRules.toggle(emptyList(), "a.b/c.D")
        assertEquals(listOf("a.b/c.D"), added)
        assertEquals(emptyList<String>(), PartyRules.toggle(added, "a.b/c.D"))
    }

    @Test
    fun `level grows with launches and stays in range`() {
        assertEquals(1, PartyRules.levelFor(0))
        assertEquals(2, PartyRules.levelFor(5))
        assertEquals(3, PartyRules.levelFor(10))
        assertEquals(100, PartyRules.levelFor(100_000))
    }
}
