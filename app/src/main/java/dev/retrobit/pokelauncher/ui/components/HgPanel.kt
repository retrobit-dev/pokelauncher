package dev.retrobit.pokelauncher.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import dev.retrobit.pokelauncher.ui.theme.HgColors

/**
 * The signature HeartGold dialog frame: dark outline, paper fill, thin gold
 * inner rule and a soft drop shadow. Built from draw calls, not images.
 */
@Composable
fun HgPanel(
    modifier: Modifier = Modifier,
    fill: Color = HgColors.Paper,
    borderColor: Color = HgColors.Ink,
    borderWidth: Dp = 2.dp,
    cornerRadius: Dp = 14.dp,
    innerRule: Boolean = false,
    contentPadding: Dp = 12.dp,
    content: @Composable BoxScope.() -> Unit,
) {
    Box(
        modifier = modifier.drawBehind {
            val w = size.width
            val h = size.height
            if (w <= 0f || h <= 0f) return@drawBehind

            val radius = cornerRadius.toPx()
            val bw = borderWidth.toPx()
            val shadowOffset = 3.dp.toPx()

            drawRoundRect(
                color = HgColors.Shadow,
                topLeft = Offset(shadowOffset, shadowOffset),
                size = Size(w, h),
                cornerRadius = CornerRadius(radius, radius),
            )
            drawRoundRect(
                color = borderColor,
                size = Size(w, h),
                cornerRadius = CornerRadius(radius, radius),
            )
            drawRoundRect(
                color = fill,
                topLeft = Offset(bw, bw),
                size = Size(w - bw * 2f, h - bw * 2f),
                cornerRadius = CornerRadius((radius - bw).coerceAtLeast(0f), (radius - bw).coerceAtLeast(0f)),
            )
            // The inner rule is decorative: keep it away from content boxes so it
            // never turns a whole panel into a gold sheet.
            if (innerRule) {
                val inset = bw + 2.dp.toPx()
                val innerRadius = (radius - inset).coerceAtLeast(0f)
                drawRoundRect(
                    color = HgColors.Gold,
                    topLeft = Offset(inset, inset),
                    size = Size(w - inset * 2f, h - inset * 2f),
                    cornerRadius = CornerRadius(innerRadius, innerRadius),
                    style = Stroke(width = 1.dp.toPx()),
                )
            }
        },
    ) {
        Box(modifier = Modifier.padding(contentPadding), content = content)
    }
}

/**
 * Inset "screen" used behind app labels and list rows: darker paper with a
 * hairline outline, like the text boxes in the DS games.
 */
@Composable
fun HgInset(
    modifier: Modifier = Modifier,
    fill: Color = HgColors.PaperDeep,
    cornerRadius: Dp = 7.dp,
    content: @Composable BoxScope.() -> Unit,
) {
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(cornerRadius))
            .background(fill)
            .drawBehind {
                drawRoundRect(
                    color = HgColors.InkFaint.copy(alpha = 0.55f),
                    size = size,
                    cornerRadius = CornerRadius(cornerRadius.toPx()),
                    style = Stroke(width = 1.dp.toPx()),
                )
            },
        content = content,
    )
}
