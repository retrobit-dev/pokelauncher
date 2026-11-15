package dev.retrobit.pokelauncher.data

/**
 * A launchable activity that can be shown on the home screen.
 *
 * [key] is stable across process death and app updates, which makes it a good
 * value to persist in the "party" (favourites) list.
 */
data class AppEntry(
    val packageName: String,
    val activityName: String,
    val label: String,
) {
    val key: String get() = "$packageName/$activityName"
}

/**
 * One of the six home screen slots.
 *
 * A slot can point at an app that is no longer installed; in that case
 * [installed] is false and the UI offers to remove it from the party.
 */
data class PartySlot(
    val key: String,
    val packageName: String,
    val activityName: String,
    val label: String,
    val installed: Boolean,
    val level: Int,
)

enum class CardStyle {
    /** HeartGold/GBA cartridge inspired tile with an inset screen. */
    Cartridge,

    /** Simple square icon tile. */
    Tile,
}

data class LauncherSettings(
    val columns: Int = 3,
    val showClock: Boolean = true,
    val cardStyle: CardStyle = CardStyle.Cartridge,
) {
    companion object {
        val COLUMN_CHOICES = listOf(2, 3, 4)
    }
}

data class LauncherUiState(
    val apps: List<AppEntry> = emptyList(),
    val party: List<PartySlot> = emptyList(),
    val settings: LauncherSettings = LauncherSettings(),
    val loading: Boolean = true,
) {
    val installedAppsByKey: Map<String, AppEntry> by lazy { apps.associateBy { it.key } }

    fun isInParty(key: String): Boolean = party.any { it.key == key }
}
