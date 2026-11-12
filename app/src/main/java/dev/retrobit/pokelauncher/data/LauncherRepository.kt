package dev.retrobit.pokelauncher.data

import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ResolveInfo
import android.graphics.drawable.Drawable
import android.net.Uri
import android.provider.Settings
import android.util.Log
import android.util.LruCache

/**
 * Everything that talks to [PackageManager] or preferences lives here so the
 * Compose layer stays free of platform calls.
 */
class LauncherRepository(private val context: Context) {

    private val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    // ------------------------------------------------------------------ apps

    /** Drawable cache: inflating icons is expensive and the grid recomposes often. */
    private val iconCache = LruCache<String, Drawable>(96)

    /**
     * Icon for [entry], or null when the app vanished between a refresh and a
     * recomposition. Never throws.
     */
    fun iconFor(entry: AppEntry): Drawable? {
        iconCache.get(entry.key)?.let { return it }
        val icon = runCatching {
            val info = context.packageManager
                .getActivityInfo(android.content.ComponentName(entry.packageName, entry.activityName), 0)
            info.loadIcon(context.packageManager)
        }.getOrNull() ?: return null
        iconCache.put(entry.key, icon)
        return icon
    }

    /**
     * All launchable activities except our own.
     *
     * Package visibility is granted by the `<queries>` block in AndroidManifest.xml,
     * so no QUERY_ALL_PACKAGES permission is required.
     */
    fun loadApps(): List<AppEntry> {
        val pm = context.packageManager
        val intent = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
        val resolved: List<ResolveInfo> = runCatching {
            pm.queryIntentActivities(intent, 0)
        }.getOrElse {
            Log.w(TAG, "queryIntentActivities failed", it)
            emptyList()
        }

        // Drop cached icons for apps that disappeared.
        val liveKeys = resolved.mapNotNull { it.activityInfo?.let { a -> "${a.packageName}/${a.name}" } }.toSet()
        runCatching {
            iconCache.snapshot().keys
                .filterNot { it in liveKeys }
                .forEach { iconCache.remove(it) }
        }

        return resolved.asSequence()
            .mapNotNull { info ->
                val activity = info.activityInfo ?: return@mapNotNull null
                if (activity.packageName == context.packageName) return@mapNotNull null
                if (!activity.enabled) return@mapNotNull null
                val label = runCatching { info.loadLabel(pm)?.toString() }
                    .getOrNull()
                    ?.trim()
                    ?.ifEmpty { null }
                    ?: activity.packageName
                AppEntry(
                    packageName = activity.packageName,
                    activityName = activity.name,
                    label = label,
                )
            }
            .distinctBy { it.key }
            .sortedWith(compareBy(String.CASE_INSENSITIVE_ORDER) { it.label })
            .toList()
    }

    fun startApp(entry: AppEntry): Boolean {
        val intent = Intent(Intent.ACTION_MAIN).apply {
            addCategory(Intent.CATEGORY_LAUNCHER)
            setClassName(entry.packageName, entry.activityName)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            addFlags(Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED)
        }
        return runCatching { context.startActivity(intent) }
            .onFailure { Log.w(TAG, "Could not launch ${entry.key}", it) }
            .isSuccess
    }

    fun openAppInfo(packageName: String): Boolean {
        val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
            data = Uri.fromParts("package", packageName, null)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        return runCatching { context.startActivity(intent) }.isSuccess
    }

    fun uninstall(packageName: String): Boolean {
        val intent = Intent(Intent.ACTION_DELETE).apply {
            data = Uri.parse("package:$packageName")
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        return runCatching { context.startActivity(intent) }.isSuccess
    }

    /**
     * Opens the system screen where the default home app is chosen.
     *
     * EMUI / HarmonyOS 4 hides [Settings.ACTION_HOME_SETTINGS] and has no
     * role manager page for HOME, so the generic intent throws and the user is
     * left guessing. The candidates are tried from the most specific to the
     * most generic; the caller shows written instructions when none of them
     * resolve.
     */
    fun openHomeSettings(): Boolean {
        val candidates = listOf(
            // EMUI / HarmonyOS home app picker.
            Intent("com.huawei.android.settings.HomeAppSettings"),
            // Standard AOSP / EMUI settings page for default apps.
            Intent(Settings.ACTION_HOME_SETTINGS),
            Intent(Settings.ACTION_MANAGE_DEFAULT_APPS_SETTINGS),
            // Last resort: the app's own details page, which still shows the
            // "Open by default" section on most ROMs.
            Intent(
                Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                Uri.fromParts("package", context.packageName, null),
            ),
        )
        for (candidate in candidates) {
            candidate.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            if (candidate.resolveActivity(context.packageManager) == null) continue
            if (runCatching { context.startActivity(candidate) }.isSuccess) return true
        }
        return false
    }

    // -------------------------------------------------------------- party

    fun loadParty(): List<String> = prefs.getString(KEY_PARTY, null)
        ?.split(SEPARATOR)
        ?.filter { it.isNotBlank() && it.contains('/') }
        ?.take(PartyRules.MAX_SLOTS)
        ?: emptyList()

    fun saveParty(keys: List<String>) {
        prefs.edit().putString(KEY_PARTY, keys.joinToString(SEPARATOR)).apply()
    }

    fun loadLaunchCount(key: String): Int = prefs.getInt("$KEY_LAUNCH_COUNT$key", 0)

    fun recordLaunch(key: String) {
        val next = loadLaunchCount(key) + 1
        prefs.edit().putInt("$KEY_LAUNCH_COUNT$key", next).apply()
    }

    // ----------------------------------------------------------- settings

    fun loadSettings(): LauncherSettings = LauncherSettings(
        columns = prefs.getInt(KEY_COLUMNS, LauncherSettings().columns)
            .takeIf { it in LauncherSettings.COLUMN_CHOICES }
            ?: LauncherSettings().columns,
        showClock = prefs.getBoolean(KEY_SHOW_CLOCK, true),
        cardStyle = runCatching {
            CardStyle.valueOf(prefs.getString(KEY_CARD_STYLE, null) ?: CardStyle.Cartridge.name)
        }.getOrDefault(CardStyle.Cartridge),
    )

    fun saveColumns(columns: Int) {
        prefs.edit().putInt(KEY_COLUMNS, columns).apply()
    }

    fun saveShowClock(show: Boolean) {
        prefs.edit().putBoolean(KEY_SHOW_CLOCK, show).apply()
    }

    fun saveCardStyle(style: CardStyle) {
        prefs.edit().putString(KEY_CARD_STYLE, style.name).apply()
    }

    companion object {
        private const val TAG = "LauncherRepository"
        private const val PREFS = "pokelauncher_prefs"
        private const val KEY_PARTY = "party_keys"
        private const val KEY_LAUNCH_COUNT = "launch_count_"
        private const val KEY_COLUMNS = "grid_columns"
        private const val KEY_SHOW_CLOCK = "show_clock"
        private const val KEY_CARD_STYLE = "card_style"

        /** Activity names never contain a newline, so it is a safe delimiter. */
        private const val SEPARATOR = "\n"
    }
}
