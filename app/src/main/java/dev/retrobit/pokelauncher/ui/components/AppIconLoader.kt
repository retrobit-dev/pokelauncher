package dev.retrobit.pokelauncher.ui.components

import android.graphics.drawable.Drawable
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import dev.retrobit.pokelauncher.data.AppEntry
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Loads an app icon off the main thread.
 *
 * Inflating a launcher icon can perform disk I/O the first time, which would
 * drop frames during the first grid layout. [produceState] keeps the result
 * cached per [AppEntry.key] for as long as the item stays composed.
 */
@Composable
fun rememberAppIcon(
    entry: AppEntry?,
    provider: (AppEntry) -> Drawable?,
): Drawable? {
    val icon by produceState<Drawable?>(initialValue = null, key1 = entry?.key) {
        val target = entry
        value = if (target == null) {
            null
        } else {
            withContext(Dispatchers.IO) { provider(target) }
        }
    }
    return icon
}
