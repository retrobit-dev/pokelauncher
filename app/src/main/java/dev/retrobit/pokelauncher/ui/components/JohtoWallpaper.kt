package dev.retrobit.pokelauncher.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.DrawScope
import dev.retrobit.pokelauncher.ui.theme.HgColors
import kotlin.math.PI
import kotlin.math.sin

/**
 * A flat illustrated Johto skyline used as the home wallpaper. Every shape is
 * drawn from code: no image assets, no copyrighted artwork. The composition is
 * deterministic so it looks the same every time the launcher redraws.
 */
@Composable
fun JohtoWallpaper(
    modifier: Modifier = Modifier,
    showSun: Boolean = true,
) {
    Canvas(modifier = modifier.fillMaxSize()) {
        val w = size.width
        val h = size.height
        if (w <= 0f || h <= 0f) return@Canvas

        // Sky.
        drawRect(
            brush = Brush.verticalGradient(
                colors = listOf(HgColors.SkyTop, HgColors.SkyBottom),
                startY = 0f,
                endY = h * 0.82f,
            ),
            size = Size(w, h),
        )

        if (showSun) {
            val sunCenter = Offset(w * 0.78f, h * 0.19f)
            val sunRadius = w * 0.085f
            drawCircle(
                color = HgColors.Sun.copy(alpha = 0.35f),
                radius = sunRadius * 1.9f,
                center = sunCenter,
            )
            drawCircle(color = HgColors.Sun, radius = sunRadius, center = sunCenter)
        }

        drawCloud(Offset(w * 0.06f, h * 0.13f), w * 0.20f)
        drawCloud(Offset(w * 0.52f, h * 0.08f), w * 0.16f)
        drawCloud(Offset(w * 0.36f, h * 0.24f), w * 0.12f)

        // Rolling hills, back to front.
        drawHill(baseY = h * 0.74f, amplitude = h * 0.10f, color = HgColors.HillFar, phase = 0.4f)
        drawHill(baseY = h * 0.80f, amplitude = h * 0.12f, color = HgColors.HillMid, phase = 2.1f)
        drawHill(baseY = h * 0.87f, amplitude = h * 0.09f, color = HgColors.HillNear, phase = 4.2f)

        // Foreground grass band.
        drawRect(
            color = HgColors.Grass,
            topLeft = Offset(0f, h * 0.93f),
            size = Size(w, h * 0.07f),
        )
        drawGrassTufts(h * 0.93f)
    }
}

private fun DrawScope.drawCloud(origin: Offset, width: Float) {
    val height = width * 0.34f
    val color = HgColors.Cloud.copy(alpha = 0.88f)
    drawOval(
        color = color,
        topLeft = origin,
        size = Size(width * 0.55f, height),
    )
    drawOval(
        color = color,
        topLeft = Offset(origin.x + width * 0.22f, origin.y - height * 0.35f),
        size = Size(width * 0.52f, height * 1.25f),
    )
    drawOval(
        color = color,
        topLeft = Offset(origin.x + width * 0.52f, origin.y + height * 0.10f),
        size = Size(width * 0.48f, height * 0.85f),
    )
}

private fun DrawScope.drawHill(baseY: Float, amplitude: Float, color: Color, phase: Float) {
    val path = Path()
    val steps = 48
    path.moveTo(0f, size.height)
    path.lineTo(0f, baseY)
    for (i in 0..steps) {
        val x = size.width * i / steps
        val angle = (i.toFloat() / steps) * 2f * PI.toFloat() + phase
        val y = baseY + sin(angle) * amplitude
        path.lineTo(x, y)
    }
    path.lineTo(size.width, size.height)
    path.close()
    drawPath(path, color)
}

private fun DrawScope.drawGrassTufts(topY: Float) {
    val tuftColor = Color(0xFF4E6B3F)
    val gap = size.width / 26f
    var x = gap / 2f
    var i = 0
    while (x < size.width) {
        val lift = if (i % 3 == 0) 6f else 3f
        val path = Path().apply {
            moveTo(x, topY + 2f)
            lineTo(x + gap * 0.14f, topY - lift)
            lineTo(x + gap * 0.28f, topY + 2f)
            close()
        }
        drawPath(path, tuftColor)
        x += gap
        i++
    }
}

/**
 * Small round "screen" used by the clock widget, drawn as a mini diorama so the
 * launcher still feels like a DS title screen.
 */
@Composable
fun MiniDiorama(modifier: Modifier = Modifier) {
    Canvas(modifier = modifier) {
        val w = size.width
        val h = size.height
        if (w <= 0f || h <= 0f) return@Canvas
        drawRect(
            brush = Brush.verticalGradient(listOf(Color(0xFFBFE3E0), Color(0xFFF6EBC6))),
            size = Size(w, h),
        )
        drawCircle(
            color = HgColors.Sun,
            radius = h * 0.18f,
            center = Offset(w * 0.72f, h * 0.30f),
        )
        val hill = Path().apply {
            moveTo(0f, h * 0.86f)
            lineTo(0f, h * 0.66f)
            lineTo(w * 0.30f, h * 0.48f)
            lineTo(w * 0.58f, h * 0.70f)
            lineTo(w * 0.82f, h * 0.52f)
            lineTo(w, h * 0.64f)
            lineTo(w, h)
            lineTo(0f, h)
            close()
        }
        drawPath(hill, HgColors.HillMid)
        val front = Path().apply {
            moveTo(0f, h)
            lineTo(0f, h * 0.82f)
            lineTo(w * 0.36f, h * 0.70f)
            lineTo(w * 0.72f, h * 0.86f)
            lineTo(w, h * 0.76f)
            lineTo(w, h)
            close()
        }
        drawPath(front, HgColors.HillNear)
    }
}
