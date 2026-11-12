package dev.retrobit.pokelauncher.data

/**
 * Pure rules for the six-slot "party" of favourite apps.
 *
 * Kept free of Android dependencies so the behaviour can be unit tested.
 */
object PartyRules {
    const val MAX_SLOTS = 6

    /** Returns the new party, or the old one when it is already full. */
    fun add(party: List<String>, key: String): List<String> {
        if (key.isBlank() || key in party) return party
        if (party.size >= MAX_SLOTS) return party
        return party + key
    }

    fun remove(party: List<String>, key: String): List<String> = party.filterNot { it == key }

    fun toggle(party: List<String>, key: String): List<String> =
        if (key in party) remove(party, key) else add(party, key)

    fun isFull(party: List<String>): Boolean = party.size >= MAX_SLOTS

    /** Party level derived from how often an app has been launched (1..100). */
    fun levelFor(launchCount: Int): Int = (1 + launchCount / 5).coerceIn(1, 100)
}
