package dev.retrobit.pokelauncher.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import dev.retrobit.pokelauncher.ui.theme.HgColors
import kotlin.math.min

/**
 * The Poké Ball, drawn from primitives so the app ships no copyrighted artwork.
 */
@Composable
fun Pokeball(
    modifier: Modifier = Modifier,
    size: Dp = 24.dp,
    top: Color = HgColors.Red,
    bottom: Color = HgColors.Cream,
    outline: Color = HgColors.Ink,
    alpha: Float = 1f,
) {
    Canvas(modifier = modifier.size(size)) {
        val radius = min(this.size.width, this.size.height) / 2f
        if (radius <= 0f) return@Canvas
        val center = Offset(this.size.width / 2f, this.size.height / 2f)
        val stroke = (radius * 0.22f).coerceAtLeast(1f)

        // Upper shell, then lower shell drawn as a half disc.
        drawCircle(color = top.copy(alpha = alpha), radius = radius, center = center)
        drawArc(
            color = bottom.copy(alpha = alpha),
            startAngle = 0f,
            sweepAngle = 180f,
            useCenter = true,
            topLeft = Offset(center.x - radius, center.y - radius),
            size = Size(radius * 2f, radius * 2f),
        )

        // Equator band.
        drawLine(
            color = outline.copy(alpha = alpha),
            start = Offset(center.x - radius, center.y),
            end = Offset(center.x + radius, center.y),
            strokeWidth = stroke,
            cap = StrokeCap.Butt,
        )

        // Outer ring and centre button.
        drawCircle(
            color = outline.copy(alpha = alpha),
            radius = radius - stroke / 2f,
            center = center,
            style = Stroke(width = stroke),
        )
        drawCircle(
            color = outline.copy(alpha = alpha),
            radius = radius * 0.34f,
            center = center,
            style = Stroke(width = stroke),
        )
        drawCircle(
            color = HgColors.Paper.copy(alpha = alpha),
            radius = radius * 0.24f,
            center = center,
        )
    }
}
