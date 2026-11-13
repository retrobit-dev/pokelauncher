package dev.retrobit.pokelauncher.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.retrobit.pokelauncher.ui.theme.HgColors
import dev.retrobit.pokelauncher.ui.theme.HgText

/** Working grid line, helper line, and "nothing goes here" red. */
private val GRID_LINE = Color(0xFF4E6E86)
private val GRID_MINOR = Color(0xFF6E8AA0)
private val GRID_DANGER = Color(0xFFC53A2D)

/**
 * The design grid, drawn straight on the screen.
 *
 * The panel is 2560x1600 px, which is 853x533 dp on this tablet. A 40 dp cell
 * divides it exactly (853/40 is not whole in dp, but 120 px is: 2560/120 = 21.3,
 * so the grid is laid out in dp and the edges are snapped in the draw). What
 * matters is that every line lands on a whole dp, so anything placed on a line
 * stays crisp at 3x density instead of sitting on a third of a pixel.
 *
 * The grid is a tool, not decoration: it is what turns "move it a bit left"
 * into "move it one cell" while the UI is being built step by step, and it is
 * off by default because a finished home screen must not show graph paper.
 */
@Composable
fun DesignGrid(
    modifier: Modifier = Modifier,
    /** One cell, in dp. 40 dp is the recommended cell for this panel. */
    cellDp: Float = GRID_DP,
    /** 8 dp helper lines: the rhythm every element should sit on. */
    showMinor: Boolean = true,
    /** The area the punch-hole camera eats. Nothing may be placed here. */
    showSafeArea: Boolean = true,
    /** Crosshair + label at the geometric centre, for centring a hero element. */
    showCentre: Boolean = true,
    opacity: Float = 0.55f,
) {
    Box(modifier = modifier.fillMaxSize()) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            val cell = cellDp.dp.toPx()
            if (cell <= 0f) return@Canvas
            val minor = if (showMinor) 8.dp.toPx() else 0f

            // 1. the 8 dp rhythm, faint.
            if (minor > 0f) {
                var x = 0f
                while (x <= size.width + 0.5f) {
                    drawLine(
                        color = GRID_MINOR.copy(alpha = opacity * 0.28f),
                        start = Offset(x, 0f),
                        end = Offset(x, size.height),
                        strokeWidth = 1f,
                    )
                    x += minor
                }
                var y = 0f
                while (y <= size.height + 0.5f) {
                    drawLine(
                        color = GRID_MINOR.copy(alpha = opacity * 0.28f),
                        start = Offset(0f, y),
                        end = Offset(size.width, y),
                        strokeWidth = 1f,
                    )
                    y += minor
                }
            }

            // 2. the working grid: one cell per 40 dp.
            var column = 0
            var x = 0f
            while (x <= size.width + 0.5f) {
                val every5 = column % 5 == 0
                drawLine(
                    color = GRID_LINE.copy(alpha = opacity * if (every5) 1f else 0.45f),
                    start = Offset(x, 0f),
                    end = Offset(x, size.height),
                    strokeWidth = if (every5) 2f else 1f,
                )
                x += cell
                column++
            }
            var row = 0
            var y = 0f
            while (y <= size.height + 0.5f) {
                val every5 = row % 5 == 0
                drawLine(
                    color = GRID_LINE.copy(alpha = opacity * if (every5) 1f else 0.45f),
                    start = Offset(0f, y),
                    end = Offset(size.width, y),
                    strokeWidth = if (every5) 2f else 1f,
                )
                y += cell
                row++
            }

            // 3. the camera box. The lens is 84 px across, 36 px in from the
            // corner, so a 64 dp square covers it with room to spare.
            if (showSafeArea) {
                val safe = 64.dp.toPx()
                drawRect(
                    color = GRID_DANGER.copy(alpha = opacity * 0.18f),
                    topLeft = Offset.Zero,
                    size = Size(safe, safe),
                )
                drawRect(
                    color = GRID_DANGER.copy(alpha = opacity),
                    topLeft = Offset.Zero,
                    size = Size(safe, safe),
                    style = Stroke(width = 2f),
                )
                // and the rest of the top strip the HUD must start below
                drawLine(
                    color = GRID_DANGER.copy(alpha = opacity * 0.7f),
                    start = Offset(safe, 0f),
                    end = Offset(safe, safe),
                    strokeWidth = 2f,
                )
            }

            // 4. centre crosshair: the point to hang a splash or a title on.
            if (showCentre) {
                val cx = size.width / 2f
                val cy = size.height / 2f
                val arm = 24.dp.toPx()
                drawLine(
                    color = GRID_LINE.copy(alpha = opacity),
                    start = Offset(cx - arm, cy),
                    end = Offset(cx + arm, cy),
                    strokeWidth = 2f,
                )
                drawLine(
                    color = GRID_LINE.copy(alpha = opacity),
                    start = Offset(cx, cy - arm),
                    end = Offset(cx, cy + arm),
                    strokeWidth = 2f,
                )
            }
        }

        // 5. the legend. Reads the real numbers from the layout, so it cannot
        // claim a grid size the lines do not use.
        if (showCentre) {
            GridLegend(modifier = Modifier.align(Alignment.BottomEnd).padding(16.dp))
        }
    }
}

@Composable
private fun GridLegend(modifier: Modifier = Modifier) {
    Row(
        modifier = modifier
            .clip(RoundedCornerShape(8.dp))
            .background(HgColors.Paper.copy(alpha = 0.92f))
            .padding(horizontal = 10.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Column {
            Text(
                text = "GRID ${GRID_DP.toInt()} dp",
                style = HgText.micro,
                fontWeight = FontWeight.Bold,
                color = HgColors.Ink,
            )
            Text(
                text = "2560 x 1600 px  ·  ${(2560 / (GRID_DP * 3)).toInt()} x ${(1600 / (GRID_DP * 3)).toInt()} sel",
                fontSize = 9.sp,
                color = HgColors.InkSoft,
            )
        }
        Spacer(Modifier.width(4.dp))
        // the three line weights, so the legend doubles as the key
        Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            Box(Modifier.size(width = 2.dp, height = 16.dp).background(GRID_LINE))
            Box(Modifier.size(width = 1.dp, height = 16.dp).background(GRID_LINE.copy(alpha = 0.45f)))
            Box(Modifier.size(width = 2.dp, height = 16.dp).background(GRID_DANGER))
        }
    }
}

/** The recommended working cell for the 2560x1600 panel: 64 x 40 cells. */
const val GRID_DP = 40f

