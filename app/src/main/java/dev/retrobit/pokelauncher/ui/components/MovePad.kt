package dev.retrobit.pokelauncher.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.ui.input.pointer.PointerEventPass
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.dp
import dev.retrobit.pokelauncher.game.Direction
import dev.retrobit.pokelauncher.game.Joystick
import dev.retrobit.pokelauncher.ui.theme.HgColors

/**
 * The on-screen pad, bottom-left of the tablet.
 *
 * Drawn rather than composed of buttons: one disc with a knob that follows the
 * thumb is what a hand expects under a thumb, and it cannot be misread as four
 * separate targets. The look is the launcher's paper and ink, so the pad does
 * not read as a bolted-on game overlay.
 *
 * The direction rule lives in [Joystick] with no Android import, so the part
 * that can be wrong (dead zone, diagonals) is unit tested on the JVM.
 */
@Composable
fun MovePad(
    onDirection: (Direction?) -> Unit,
    modifier: Modifier = Modifier,
) {
    val density = LocalDensity.current
    // Explicit names, not `radius`/`knob`: inside the Canvas these are already
    // DrawScope properties, and a local of the same name shadows one and is
    // silently wrong for the other.
    val padPx = with(density) { Joystick.RADIUS_DP.dp.toPx() }
    val knobPx = with(density) { Joystick.KNOB_DP.dp.toPx() }
    var thumb by remember { mutableStateOf(Offset.Zero) }

    Canvas(
        modifier = modifier
            // dp, not px: toDp() is only available inside a Density receiver,
            // and this is the composable scope.
            .size((Joystick.RADIUS_DP * 2).dp)
            .pointerInput(padPx) {
                // One gesture at a time, from the first finger down to the last
                // finger up. Written with awaitPointerEventScope rather than
                // awaitEachGesture because the loop has to end on a *release*,
                // not on a condition: breaking out of awaitEachGesture early
                // leaves it waiting for the next down while the pad still thinks
                // a thumb is on it.
                awaitPointerEventScope {
                    while (true) {
                        val down = awaitFirstDown(requireUnconsumed = false)
                        val centre = Offset(size.width / 2f, size.height / 2f)

                        // Report the first direction immediately: waiting for a
                        // move would make the pad feel like it dropped the touch.
                        var reported = Joystick.direction(
                            down.position.x - centre.x, down.position.y - centre.y, padPx,
                        )
                        onDirection(reported)
                        thumb = Offset(down.position.x - centre.x, down.position.y - centre.y)

                        var pressed = true
                        while (pressed) {
                            val event = awaitPointerEvent(PointerEventPass.Main)
                            val change = event.changes.firstOrNull { it.id == down.id }
                            if (change == null) {
                                // The pointer disappeared without a release
                                // event: treat it as lifted, never as stuck.
                                pressed = false
                                break
                            }
                            if (!change.pressed) {
                                pressed = false
                                break
                            }
                            val dx = change.position.x - centre.x
                            val dy = change.position.y - centre.y
                            thumb = Offset(dx, dy)
                            val next = Joystick.direction(dx, dy, padPx)
                            if (next != reported) {
                                reported = next
                                onDirection(next)
                            }
                            change.consume()
                        }

                        // Lifting off always stops the walk, even if the finger
                        // was still inside the dead zone when it left the glass.
                        thumb = Offset.Zero
                        onDirection(null)
                    }
                }
            },
    ) {
        val centre = Offset(size.width / 2f, size.height / 2f)
        drawCircle(color = HgColors.Paper.copy(alpha = 0.55f), radius = padPx)
        drawCircle(
            color = HgColors.Ink.copy(alpha = 0.55f),
            radius = padPx,
            style = Stroke(width = 2.dp.toPx()),
        )
        // a faint cross, so the four directions are legible without four buttons
        val arm = padPx * 0.55f
        drawLine(HgColors.Ink.copy(alpha = 0.12f), centre - Offset(arm, 0f), centre + Offset(arm, 0f), 1.dp.toPx())
        drawLine(HgColors.Ink.copy(alpha = 0.12f), centre - Offset(0f, arm), centre + Offset(0f, arm), 1.dp.toPx())

        val clamped = Joystick.knob(thumb.x, thumb.y, padPx)
        drawCircle(
            color = HgColors.Paper,
            radius = knobPx,
            center = centre + Offset(clamped.first, clamped.second),
        )
        drawCircle(
            color = HgColors.Ink.copy(alpha = 0.75f),
            radius = knobPx,
            center = centre + Offset(clamped.first, clamped.second),
            style = Stroke(width = 2.dp.toPx()),
        )
    }
}
