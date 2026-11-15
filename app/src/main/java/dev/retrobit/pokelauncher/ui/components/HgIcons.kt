package dev.retrobit.pokelauncher.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import dev.retrobit.pokelauncher.ui.theme.HgColors
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.sin

/**
 * Small vector icons drawn with Canvas primitives.
 *
 * The pixel fonts shipped with the launcher (Press Start 2P, DotGothic16,
 * Silkscreen) do not contain glyphs for symbols such as the gear or the X, so
 * text glyphs would render as tofu boxes. Drawing them keeps the launcher
 * self contained and sharp at any density.
 */
@Composable
fun CloseIcon(
    modifier: Modifier = Modifier,
    size: Dp = 16.dp,
    color: Color = HgColors.Ink,
    strokeWidth: Dp = 2.dp,
) {
    Canvas(modifier = modifier.size(size)) {
        val pad = strokeWidth.toPx()
        drawLine(
            color = color,
            start = Offset(pad, pad),
            end = Offset(this.size.width - pad, this.size.height - pad),
            strokeWidth = strokeWidth.toPx(),
            cap = StrokeCap.Round,
        )
        drawLine(
            color = color,
            start = Offset(this.size.width - pad, pad),
            end = Offset(pad, this.size.height - pad),
            strokeWidth = strokeWidth.toPx(),
            cap = StrokeCap.Round,
        )
    }
}

@Composable
fun MenuIcon(
    modifier: Modifier = Modifier,
    size: Dp = 18.dp,
    color: Color = HgColors.Ink,
) {
    Canvas(modifier = modifier.size(size)) {
        val barHeight = this.size.height * 0.12f
        val gap = this.size.height * 0.20f
        repeat(3) { index ->
            drawRoundRect(
                color = color,
                topLeft = Offset(0f, index * gap),
                size = Size(this.size.width, barHeight),
                cornerRadius = CornerRadius(barHeight / 2f, barHeight / 2f),
            )
        }
    }
}

@Composable
fun GearIcon(
    modifier: Modifier = Modifier,
    size: Dp = 20.dp,
    color: Color = HgColors.Ink,
) {
    Canvas(modifier = modifier.size(size)) {
        val radius = min(this.size.width, this.size.height) / 2f
        val center = Offset(this.size.width / 2f, this.size.height / 2f)
        val toothLength = radius * 0.28f
        val ringRadius = radius * 0.58f

        // Eight teeth around the ring.
        repeat(8) { index ->
            val angle = Math.toRadians(index * 45.0)
            val dx = cos(angle).toFloat()
            val dy = sin(angle).toFloat()
            drawLine(
                color = color,
                start = Offset(center.x + dx * ringRadius, center.y + dy * ringRadius),
                end = Offset(center.x + dx * (ringRadius + toothLength), center.y + dy * (ringRadius + toothLength)),
                strokeWidth = radius * 0.30f,
                cap = StrokeCap.Round,
            )
        }
        drawCircle(color = color, radius = ringRadius, center = center, style = Stroke(width = radius * 0.24f))
        drawCircle(color = HgColors.Paper, radius = ringRadius * 0.45f, center = center)
    }
}

@Composable
fun SearchIcon(
    modifier: Modifier = Modifier,
    size: Dp = 16.dp,
    color: Color = HgColors.InkSoft,
) {
    Canvas(modifier = modifier.size(size)) {
        val radius = this.size.width * 0.30f
        val center = Offset(this.size.width * 0.40f, this.size.height * 0.40f)
        drawCircle(color = color, radius = radius, center = center, style = Stroke(width = this.size.width * 0.11f))
        val handleStart = Offset(center.x + radius * 0.75f, center.y + radius * 0.75f)
        drawLine(
            color = color,
            start = handleStart,
            end = Offset(this.size.width * 0.92f, this.size.height * 0.92f),
            strokeWidth = this.size.width * 0.12f,
            cap = StrokeCap.Round,
        )
    }
}

@Composable
fun ChevronIcon(
    modifier: Modifier = Modifier,
    size: Dp = 14.dp,
    color: Color = HgColors.InkFaint,
) {
    Canvas(modifier = modifier.size(size)) {
        val w = this.size.width
        val h = this.size.height
        val stroke = w * 0.16f
        val path = androidx.compose.ui.graphics.Path().apply {
            moveTo(w * 0.36f, h * 0.20f)
            lineTo(w * 0.66f, h * 0.50f)
            lineTo(w * 0.36f, h * 0.80f)
        }
        drawPath(path, color = color, style = Stroke(width = stroke, cap = StrokeCap.Round))
    }
}

@Composable
fun PlusIcon(
    modifier: Modifier = Modifier,
    size: Dp = 18.dp,
    color: Color = HgColors.InkFaint,
) {
    Canvas(modifier = modifier.size(size)) {
        val stroke = this.size.width * 0.14f
        drawLine(
            color = color,
            start = Offset(this.size.width / 2f, stroke),
            end = Offset(this.size.width / 2f, this.size.height - stroke),
            strokeWidth = stroke,
            cap = StrokeCap.Round,
        )
        drawLine(
            color = color,
            start = Offset(stroke, this.size.height / 2f),
            end = Offset(this.size.width - stroke, this.size.height / 2f),
            strokeWidth = stroke,
            cap = StrokeCap.Round,
        )
    }
}
