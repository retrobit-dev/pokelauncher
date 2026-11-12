package dev.retrobit.pokelauncher.ui.components

import android.graphics.drawable.Drawable
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.clipPath
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.core.graphics.drawable.toBitmap
import dev.retrobit.pokelauncher.R
import dev.retrobit.pokelauncher.data.CardStyle
import dev.retrobit.pokelauncher.data.PartySlot
import dev.retrobit.pokelauncher.ui.theme.HgColors
import dev.retrobit.pokelauncher.ui.theme.HgText

/**
 * Builds the GBA cartridge silhouette: clipped top corners and the little
 * notch on the lower half, like a HeartGold cart ridge.
 */
private fun cartridgePath(w: Float, h: Float): Path {
    val cut = w * 0.10f
    val notch = w * 0.075f
    return Path().apply {
        moveTo(cut, 0f)
        lineTo(w - cut, 0f)
        lineTo(w, cut)
        lineTo(w, h * 0.70f)
        lineTo(w - notch, h * 0.78f)
        lineTo(w - notch, h * 0.92f)
        lineTo(w - notch * 0.55f, h)
        lineTo(notch * 0.55f, h)
        lineTo(notch, h * 0.92f)
        lineTo(notch, h * 0.78f)
        lineTo(0f, h * 0.70f)
        lineTo(0f, cut)
        close()
    }
}

@Composable
fun PartySlotCard(
    slot: PartySlot?,
    icon: Drawable?,
    style: CardStyle,
    slotIndex: Int,
    modifier: Modifier = Modifier,
    onClick: () -> Unit,
    onLongClick: () -> Unit = {},
) {
    if (slot == null) {
        EmptySlotCard(modifier = modifier, onClick = onClick)
        return
    }
    when (style) {
        CardStyle.Cartridge -> CartridgeCard(slot, icon, slotIndex, modifier, onClick, onLongClick)
        CardStyle.Tile -> TileCard(slot, icon, modifier, onClick, onLongClick)
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun CartridgeCard(
    slot: PartySlot,
    icon: Drawable?,
    slotIndex: Int,
    modifier: Modifier = Modifier,
    onClick: () -> Unit,
    onLongClick: () -> Unit,
) {
    val (body, shade) = HgColors.cartridge(slotIndex)
    val interaction = remember { MutableInteractionSource() }
    val pressed by interaction.collectIsPressedAsState()
    val lift by animateDpAsState(if (pressed) 3.dp else 0.dp, label = "cardLift")
    val label = if (slot.installed) slot.label else stringResource(R.string.slot_unknown_name)

    Column(
        modifier = modifier
            .offset(y = lift)
            .semantics { contentDescription = slot.label }
            .combinedClickable(
                interactionSource = interaction,
                indication = null,
                onClick = onClick,
                onLongClick = onLongClick,
            ),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(0.92f)
                .drawBehind {
                    val w = size.width
                    val h = size.height
                    val path = cartridgePath(w, h)

                    drawPath(
                        path = cartridgePath(w, h).apply { translate(Offset(0f, 3.dp.toPx())) },
                        color = HgColors.Shadow,
                    )
                    drawPath(path, color = body)
                    clipPath(path) {
                        drawRect(
                            color = shade,
                            topLeft = Offset(0f, h * 0.74f),
                            size = Size(w, h * 0.26f),
                        )
                        drawRect(
                            color = Color.White.copy(alpha = 0.22f),
                            topLeft = Offset(w * 0.16f, h * 0.030f),
                            size = Size(w * 0.68f, h * 0.028f),
                        )
                    }
                    drawPath(path, color = HgColors.Ink, style = Stroke(width = 2.dp.toPx()))

                    val gripY = h * 0.945f
                    for (i in 0..1) {
                        drawLine(
                            color = HgColors.Ink.copy(alpha = 0.4f),
                            start = Offset(w * 0.42f, gripY + i * 2.5.dp.toPx()),
                            end = Offset(w * 0.58f, gripY + i * 2.5.dp.toPx()),
                            strokeWidth = 1.dp.toPx(),
                        )
                    }
                },
            contentAlignment = Alignment.TopCenter,
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth(0.78f)
                    .padding(top = 16.dp)
                    .aspectRatio(1.15f)
                    .clip(RoundedCornerShape(6.dp))
                    .background(HgColors.ScreenInk)
                    .drawBehind {
                        drawRoundRect(
                            color = HgColors.Cream.copy(alpha = 0.85f),
                            size = size,
                            cornerRadius = CornerRadius(6.dp.toPx()),
                            style = Stroke(width = 1.5.dp.toPx()),
                        )
                    },
                contentAlignment = Alignment.Center,
            ) {
                if (icon != null && slot.installed) {
                    AppIcon(icon = icon, label = slot.label, size = 40.dp)
                } else {
                    Text(text = "?", style = HgText.clock.copy(color = HgColors.Cream))
                }
            }

            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 3.dp, start = 8.dp, end = 8.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = stringResource(R.string.slot_level, slot.level),
                    style = HgText.tiny.copy(color = HgColors.Ink),
                )
                Pokeball(size = 10.dp, alpha = if (slot.installed) 1f else 0.4f)
            }
        }

        Spacer(Modifier.height(5.dp))
        HgInset(modifier = Modifier.fillMaxWidth()) {
            Text(
                text = label,
                style = HgText.small.copy(
                    color = if (slot.installed) HgColors.Ink else HgColors.InkFaint,
                ),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                textAlign = TextAlign.Center,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 5.dp, vertical = 2.dp),
            )
        }
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun TileCard(
    slot: PartySlot,
    icon: Drawable?,
    modifier: Modifier = Modifier,
    onClick: () -> Unit,
    onLongClick: () -> Unit,
) {
    val interaction = remember { MutableInteractionSource() }
    val pressed by interaction.collectIsPressedAsState()
    val lift by animateDpAsState(if (pressed) 2.dp else 0.dp, label = "tileLift")

    Column(
        modifier = modifier
            .offset(y = lift)
            .semantics { contentDescription = slot.label }
            .combinedClickable(
                interactionSource = interaction,
                indication = null,
                onClick = onClick,
                onLongClick = onLongClick,
            ),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(1f)
                .drawBehind {
                    val w = size.width
                    val h = size.height
                    val r = 14.dp.toPx()
                    drawRoundRect(
                        color = HgColors.Shadow,
                        topLeft = Offset(3.dp.toPx(), 3.dp.toPx()),
                        size = Size(w, h),
                        cornerRadius = CornerRadius(r, r),
                    )
                    drawRoundRect(
                        color = HgColors.Ink,
                        size = Size(w, h),
                        cornerRadius = CornerRadius(r, r),
                    )
                    drawRoundRect(
                        color = HgColors.Cream,
                        topLeft = Offset(2.dp.toPx(), 2.dp.toPx()),
                        size = Size(w - 4.dp.toPx(), h - 4.dp.toPx()),
                        cornerRadius = CornerRadius(r - 2.dp.toPx(), r - 2.dp.toPx()),
                    )
                    drawRoundRect(
                        color = HgColors.Gold,
                        topLeft = Offset(5.dp.toPx(), 5.dp.toPx()),
                        size = Size(w - 10.dp.toPx(), h - 10.dp.toPx()),
                        cornerRadius = CornerRadius(r - 5.dp.toPx(), r - 5.dp.toPx()),
                        style = Stroke(width = 1.dp.toPx()),
                    )
                },
            contentAlignment = Alignment.Center,
        ) {
            if (icon != null && slot.installed) {
                AppIcon(icon = icon, label = slot.label, size = 46.dp)
            } else {
                Text(text = "?", style = HgText.title.copy(color = HgColors.InkFaint))
            }
        }
        Spacer(Modifier.height(5.dp))
        Text(
            text = if (slot.installed) slot.label else stringResource(R.string.slot_unknown_name),
            style = HgText.small,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            textAlign = TextAlign.Center,
            modifier = Modifier
                .fillMaxWidth()
                .alpha(if (slot.installed) 1f else 0.5f),
        )
    }
}

@Composable
private fun EmptySlotCard(modifier: Modifier = Modifier, onClick: () -> Unit) {
    val addLabel = stringResource(R.string.slot_add)
    Column(
        modifier = modifier
            .semantics { contentDescription = addLabel }
            .clickable(
                interactionSource = remember { MutableInteractionSource() },
                indication = null,
                onClick = onClick,
            ),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(0.92f)
                .drawBehind {
                    val path = cartridgePath(size.width, size.height)
                    drawPath(path, color = HgColors.PaperDeep.copy(alpha = 0.40f))
                    drawPath(
                        path = path,
                        color = HgColors.InkFaint.copy(alpha = 0.75f),
                        style = Stroke(width = 1.5.dp.toPx()),
                    )
                },
            contentAlignment = Alignment.Center,
        ) {
            PlusIcon(size = 20.dp)
        }
        Spacer(Modifier.height(5.dp))
        Text(text = stringResource(R.string.slot_empty_letter), style = HgText.small.copy(color = HgColors.InkFaint))
    }
}

@Composable
fun AppIcon(
    icon: Drawable,
    label: String,
    size: Dp,
    modifier: Modifier = Modifier,
) {
    val iconDescription = stringResource(R.string.cd_app_icon, label)
    val bitmap = remember(icon, size) {
        runCatching { icon.toBitmap(width = 144, height = 144).asImageBitmap() }.getOrNull()
    }
    if (bitmap != null) {
        Image(
            bitmap = bitmap,
            contentDescription = iconDescription,
            modifier = modifier.size(size),
            contentScale = ContentScale.Fit,
        )
    } else {
        Box(
            modifier = modifier
                .size(size)
                .clip(RoundedCornerShape(6.dp))
                .background(HgColors.PaperShade),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                text = label.take(1).uppercase(),
                style = HgText.body.copy(color = HgColors.Ink),
            )
        }
    }
}

/** Six small Poké Balls, filled according to the party size. */
@Composable
fun PartyIndicator(count: Int, modifier: Modifier = Modifier, max: Int = 6) {
    Row(
        modifier = modifier,
        horizontalArrangement = Arrangement.spacedBy(3.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        repeat(max) { index ->
            if (index < count) {
                Pokeball(size = 9.dp)
            } else {
                Box(
                    modifier = Modifier
                        .size(9.dp)
                        .clip(CircleShape)
                        .background(HgColors.InkFaint.copy(alpha = 0.22f)),
                )
            }
        }
    }
}
