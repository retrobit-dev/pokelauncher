package dev.retrobit.pokelauncher.ui.components

import androidx.compose.animation.core.animateDpAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import dev.retrobit.pokelauncher.ui.theme.HgColors
import dev.retrobit.pokelauncher.ui.theme.HgText

/**
 * A chunky HeartGold style button: dark outline, paper face, gold inner rule.
 * Pressing sinks the face a couple of pixels instead of showing a ripple.
 */
@Composable
fun HgButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    fill: Color = HgColors.PaperDeep,
    accent: Color = HgColors.Gold,
    textStyle: TextStyle = HgText.badge,
    leading: (@Composable () -> Unit)? = null,
    contentDescription: String? = null,
    minHeight: Dp = 44.dp,
    horizontalPadding: Dp = 14.dp,
) {
    val interaction = remember { MutableInteractionSource() }
    val pressed by interaction.collectIsPressedAsState()
    val sink by animateDpAsState(if (pressed) 2.dp else 0.dp, label = "sink")
    val alpha = if (enabled) 1f else 0.45f

    val semanticsModifier = if (contentDescription != null) {
        Modifier.semantics { this.contentDescription = contentDescription }
    } else {
        Modifier
    }

    Box(
        modifier = modifier
            .heightIn(min = minHeight)
            .then(semanticsModifier)
            .clip(RoundedCornerShape(10.dp))
            .clickable(
                interactionSource = interaction,
                indication = null,
                enabled = enabled,
                onClick = onClick,
            )
            .drawBehind {
                val w = size.width
                val h = size.height
                val r = 10.dp.toPx()
                val dy = sink.toPx()

                drawRoundRect(
                    color = HgColors.Shadow.copy(alpha = 0.35f * alpha),
                    topLeft = Offset(0f, dy + 2.dp.toPx()),
                    size = Size(w, h - 2.dp.toPx()),
                    cornerRadius = CornerRadius(r, r),
                )
                drawRoundRect(
                    color = HgColors.Ink.copy(alpha = alpha),
                    topLeft = Offset(0f, dy),
                    size = Size(w, h - 2.dp.toPx()),
                    cornerRadius = CornerRadius(r, r),
                )
                drawRoundRect(
                    color = fill.copy(alpha = alpha),
                    topLeft = Offset(2.dp.toPx(), dy + 2.dp.toPx()),
                    size = Size(w - 4.dp.toPx(), h - 6.dp.toPx()),
                    cornerRadius = CornerRadius(r - 2.dp.toPx(), r - 2.dp.toPx()),
                )
                drawRoundRect(
                    color = accent.copy(alpha = alpha),
                    topLeft = Offset(5.dp.toPx(), dy + 5.dp.toPx()),
                    size = Size(w - 10.dp.toPx(), h - 12.dp.toPx()),
                    cornerRadius = CornerRadius(r - 5.dp.toPx(), r - 5.dp.toPx()),
                    style = Stroke(width = 1.dp.toPx()),
                )
            },
    ) {
        Row(
            modifier = Modifier
                .align(Alignment.Center)
                .padding(horizontal = horizontalPadding, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            if (leading != null) {
                Box(modifier = Modifier.size(18.dp), contentAlignment = Alignment.Center) {
                    leading()
                }
                Spacer(Modifier.width(8.dp))
            }
            Text(
                text = text,
                style = textStyle.copy(color = textStyle.color.copy(alpha = alpha)),
                textAlign = TextAlign.Center,
            )
        }
    }
}

/** Round icon button used in the top bar (settings, menu). */
@Composable
fun HgIconButton(
    onClick: () -> Unit,
    contentDescription: String,
    modifier: Modifier = Modifier,
    size: Dp = 46.dp,
    content: @Composable () -> Unit,
) {
    Box(
        modifier = modifier
            .size(size)
            .clip(CircleShape)
            .background(HgColors.Paper)
            .border(2.dp, HgColors.Ink, CircleShape)
            .clickable(
                interactionSource = remember { MutableInteractionSource() },
                indication = null,
                onClick = onClick,
            )
            .semantics { this.contentDescription = contentDescription },
        contentAlignment = Alignment.Center,
    ) {
        content()
    }
}
