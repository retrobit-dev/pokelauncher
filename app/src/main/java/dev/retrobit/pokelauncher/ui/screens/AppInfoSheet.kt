package dev.retrobit.pokelauncher.ui.screens

import android.graphics.drawable.Drawable
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import dev.retrobit.pokelauncher.R
import dev.retrobit.pokelauncher.data.AppEntry
import dev.retrobit.pokelauncher.ui.components.AppIcon
import dev.retrobit.pokelauncher.ui.components.HgButton
import dev.retrobit.pokelauncher.ui.components.HgPanel
import dev.retrobit.pokelauncher.ui.components.Pokeball
import dev.retrobit.pokelauncher.ui.theme.HgColors
import dev.retrobit.pokelauncher.ui.theme.HgText

/**
 * App details sheet shown on long press: launch, system settings, uninstall and
 * the party toggle.
 */
@Composable
fun AppInfoSheet(
    entry: AppEntry?,
    isFavourite: Boolean,
    icon: Drawable?,
    onDismiss: () -> Unit,
    onOpen: (AppEntry) -> Unit,
    onAppInfo: (AppEntry) -> Unit,
    onUninstall: (AppEntry) -> Unit,
    onToggleFavourite: (AppEntry) -> Unit,
) {
    AnimatedVisibility(
        visible = entry != null,
        enter = fadeIn() + slideInVertically { it },
        exit = fadeOut() + slideOutVertically { it },
    ) {
        val current = entry ?: return@AnimatedVisibility
        Box(modifier = Modifier.fillMaxSize()) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(Color.Black.copy(alpha = 0.35f))
                    .clickable(onClick = onDismiss),
            )
            Column(
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .fillMaxWidth()
                    .padding(12.dp)
                    .navigationBarsPadding(),
            ) {
                HgPanel(
                    modifier = Modifier.fillMaxWidth(),
                    cornerRadius = 16.dp,
                    contentPadding = 14.dp,
                ) {
                    Column {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(56.dp)
                                    .clip(RoundedCornerShape(12.dp))
                                    .background(HgColors.PaperDeep),
                                contentAlignment = Alignment.Center,
                            ) {
                                if (icon != null) {
                                    AppIcon(icon = icon, label = current.label, size = 42.dp)
                                } else {
                                    Text(text = "?", style = HgText.title)
                                }
                            }
                            Spacer(Modifier.width(12.dp))
                            Column(modifier = Modifier.weight(1f)) {
                                Text(text = current.label, style = HgText.title)
                                Spacer(Modifier.height(2.dp))
                                Text(text = current.packageName, style = HgText.tiny)
                            }
                            Pokeball(
                                size = 26.dp,
                                alpha = if (isFavourite) 1f else 0.55f,
                            )
                        }
                        Spacer(Modifier.height(14.dp))
                        Row {
                            HgButton(
                                text = stringResource(R.string.info_open),
                                onClick = { onOpen(current) },
                                modifier = Modifier.weight(1f),
                                fill = HgColors.Gold,
                            )
                            Spacer(Modifier.width(8.dp))
                            HgButton(
                                text = stringResource(
                                    if (isFavourite) R.string.info_party_remove else R.string.info_party_add,
                                ),
                                onClick = { onToggleFavourite(current) },
                                modifier = Modifier.weight(1f),
                                fill = HgColors.PaperDeep,
                            )
                        }
                        Spacer(Modifier.height(8.dp))
                        Row {
                            HgButton(
                                text = stringResource(R.string.info_system),
                                onClick = { onAppInfo(current) },
                                modifier = Modifier.weight(1f),
                                fill = HgColors.Cream,
                            )
                            Spacer(Modifier.width(8.dp))
                            HgButton(
                                text = stringResource(R.string.info_uninstall),
                                onClick = { onUninstall(current) },
                                modifier = Modifier.weight(1f),
                                fill = HgColors.Cream,
                                accent = HgColors.Red,
                                textStyle = HgText.badge,
                            )
                        }
                    }
                }
            }
        }
    }
}
