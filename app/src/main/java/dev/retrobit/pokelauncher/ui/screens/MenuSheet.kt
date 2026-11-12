package dev.retrobit.pokelauncher.ui.screens

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
import dev.retrobit.pokelauncher.ui.components.ChevronIcon
import dev.retrobit.pokelauncher.ui.components.CloseIcon
import dev.retrobit.pokelauncher.ui.components.HgPanel
import dev.retrobit.pokelauncher.ui.components.Pokeball
import dev.retrobit.pokelauncher.ui.theme.HgText

/**
 * Bottom "START menu" sheet, the HeartGold style list of actions.
 */
@Composable
fun MenuSheet(
    visible: Boolean,
    onDismiss: () -> Unit,
    onAllApps: () -> Unit,
    onSettings: () -> Unit,
    onSetDefault: () -> Unit,
) {
    AnimatedVisibility(
        visible = visible,
        enter = fadeIn() + slideInVertically { it },
        exit = fadeOut() + slideOutVertically { it },
    ) {
        Box(modifier = Modifier.fillMaxSize()) {
            // Tap-out scrim.
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
                    contentPadding = 12.dp,
                ) {
                    Column {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Pokeball(size = 20.dp)
                            Spacer(Modifier.width(8.dp))
                            Column(modifier = Modifier.weight(1f)) {
                                Text(text = stringResource(R.string.menu_title), style = HgText.heading)
                                Text(text = stringResource(R.string.menu_subtitle), style = HgText.micro)
                            }
                            Box(
                                modifier = Modifier
                                    .size(32.dp)
                                    .clip(RoundedCornerShape(8.dp))
                                    .clickable(onClick = onDismiss),
                                contentAlignment = Alignment.Center,
                            ) {
                                CloseIcon(size = 14.dp)
                            }
                        }
                        Spacer(Modifier.height(10.dp))
                        MenuRow(stringResource(R.string.menu_all_apps), onAllApps)
                        MenuRow(stringResource(R.string.menu_settings), onSettings)
                        MenuRow(stringResource(R.string.menu_set_default), onSetDefault)
                    }
                }
            }
        }
    }
}

@Composable
private fun MenuRow(label: String, onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(10.dp))
            .clickable(onClick = onClick)
            .padding(horizontal = 10.dp, vertical = 13.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Pokeball(size = 14.dp)
        Spacer(Modifier.width(10.dp))
        Text(text = label, style = HgText.body)
        Spacer(Modifier.weight(1f))
        ChevronIcon(size = 14.dp)
    }
}
