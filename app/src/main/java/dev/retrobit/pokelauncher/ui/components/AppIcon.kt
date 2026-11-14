package dev.retrobit.pokelauncher.ui.components

import android.graphics.drawable.Drawable
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.core.graphics.drawable.toBitmap
import dev.retrobit.pokelauncher.R
import dev.retrobit.pokelauncher.ui.theme.HgColors
import dev.retrobit.pokelauncher.ui.theme.HgText

/**
 * One app icon at a fixed size: the real launcher icon when we could load it,
 * otherwise the first letter of the label on a paper tile. Used by the app
 * drawer, the app info sheet and the "all apps" list.
 */
@Composable
fun AppIcon(
    icon: Drawable,
    label: String,
    size: Dp,
    modifier: Modifier = Modifier,
) {
    val iconDescription = stringResource(R.string.cd_app_icon, label)
    val bitmap = remember(icon, size) {
        runCatching { icon.toBitmap(width = 144, height = 144).asImageBitmap() }.getOrNull()
    }
    if (bitmap != null) {
        Image(
            bitmap = bitmap,
            contentDescription = iconDescription,
            modifier = modifier.size(size),
            contentScale = ContentScale.Fit,
        )
    } else {
        Box(
            modifier = modifier
                .size(size)
                .clip(RoundedCornerShape(6.dp))
                .background(HgColors.PaperShade),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                text = label.take(1).uppercase(),
                style = HgText.body.copy(color = HgColors.Ink),
            )
        }
    }
}
