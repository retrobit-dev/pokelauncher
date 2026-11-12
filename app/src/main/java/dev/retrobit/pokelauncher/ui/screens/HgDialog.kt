package dev.retrobit.pokelauncher.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import dev.retrobit.pokelauncher.ui.components.HgButton
import dev.retrobit.pokelauncher.ui.components.HgPanel
import dev.retrobit.pokelauncher.ui.theme.HgColors
import dev.retrobit.pokelauncher.ui.theme.HgText

/**
 * HeartGold message box dialog: dark scrim, paper panel, title in red caps and
 * two chunky buttons.
 */
@Composable
fun HgDialog(
    title: String,
    body: String,
    confirmLabel: String,
    onConfirm: () -> Unit,
    onDismiss: () -> Unit,
    dismissLabel: String? = null,
) {
    Dialog(onDismissRequest = onDismiss) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(Color.Transparent, RoundedCornerShape(16.dp)),
        ) {
            HgPanel(
                modifier = Modifier.fillMaxWidth(),
                cornerRadius = 16.dp,
                contentPadding = 16.dp,
            ) {
                Column {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .height(18.dp)
                                .width(4.dp)
                                .background(HgColors.Red, RoundedCornerShape(2.dp)),
                        )
                        Spacer(Modifier.width(8.dp))
                        Text(text = title, style = HgText.heading.copy(color = HgColors.RedDeep))
                    }
                    Spacer(Modifier.height(10.dp))
                    Text(text = body, style = HgText.bodySoft)
                    Spacer(Modifier.height(16.dp))
                    Row(modifier = Modifier.fillMaxWidth()) {
                        if (dismissLabel != null) {
                            HgButton(
                                text = dismissLabel,
                                onClick = onDismiss,
                                modifier = Modifier.weight(1f),
                                fill = HgColors.Cream,
                            )
                            Spacer(Modifier.width(8.dp))
                        }
                        HgButton(
                            text = confirmLabel,
                            onClick = onConfirm,
                            modifier = Modifier.weight(1f),
                            fill = HgColors.Gold,
                        )
                    }
                }
            }
        }
    }
}
