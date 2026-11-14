package dev.retrobit.pokelauncher.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.FilterQuality
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.input.pointer.pointerInput
import dev.retrobit.pokelauncher.game.Camera
import dev.retrobit.pokelauncher.game.Direction
import dev.retrobit.pokelauncher.game.GameMap
import dev.retrobit.pokelauncher.game.PlayerSprite
import dev.retrobit.pokelauncher.game.TileSet
import dev.retrobit.pokelauncher.game.TouchInput

/**
 * Draws the world, one 16px tile at a time.
 *
 * Two rules carry the HeartGold look and both are easy to lose:
 *
 *  1. `FilterQuality.None`. Any smoothing turns crisp 16px pixels into mush,
 *     especially doubled on a 343ppi panel.
 *  2. Integer scale. The camera is in map pixels and the canvas is scaled by a
 *     whole number, so a tile is always exactly 16, 32, 48... screen pixels.
 *
 * The draw loop skips the two layers above ground when the cell has none, so a
 * plain lawn costs one draw call per cell instead of three.
 */
@Composable
fun WorldCanvas(
    map: GameMap,
    tiles: TileSet,
    atlas: ImageBitmap?,
    /** Walk sheet: 2 frames wide, one row per direction. Null falls back to ink. */
    playerSheet: ImageBitmap?,
    camera: Camera,
    playerX: Int,
    playerY: Int,
    facing: Direction,
    /** Alternates each step so the legs move while the player is walking. */
    stepParity: Boolean,
    walking: Boolean,
    scale: Int,
    nightAmount: Float,
    litAt: (Int, Int) -> Boolean,
    builtAt: (Int, Int) -> Boolean,
    cropsAt: (Int, Int) -> Int,
    onCellTap: (Int, Int) -> Unit,
    onZoom: (Int) -> Unit = {},
    modifier: Modifier = Modifier,
) {
    Box(
        modifier = modifier
            .background(Color(0xFF5C7A45))
            .pointerInput(atlas, camera, scale) {
                detectTapGestures { offset ->
                    // offset is in screen pixels; the camera is in map pixels
                    val mapX = offset.x / scale
                    val mapY = offset.y / scale
                    val (cx, cy) = TouchInput.cellAt(mapX, mapY, camera)
                    onCellTap(cx, cy)
                }
            }
            .pointerInput(Unit) {
                detectTransformGestures { _, _, zoom, _ ->
                    // the caller owns the scale, the gesture only asks for a step
                    if (zoom > 1.25f) onZoom(1) else if (zoom < 0.8f) onZoom(-1)
                }
            },
    ) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            if (atlas == null) return@Canvas

            val px = (16 * scale).toFloat()
            drawMap(map, tiles, atlas, camera, scale, px)

            // the player: a 16px frame from the walk sheet, drawn at the same
            // integer scale as the tiles so it never resamples
            val pScreenX = playerX * px - camera.x * scale
            val pScreenY = playerY * px - camera.y * scale
            drawPlayer(pScreenX, pScreenY, px, facing, stepParity, walking, playerSheet)

            // built blocks sit above the map layer
            for ((x, y, _) in map.entries()) {
                if (!builtAt(x, y)) continue
                val bx = x * px - camera.x * scale
                val by = y * px - camera.y * scale
                drawRect(
                    color = Color(0xFF9A8768),
                    topLeft = Offset(bx, by),
                    size = androidx.compose.ui.geometry.Size(px, px),
                )
                drawRect(
                    color = Color(0xFF6B5B44),
                    topLeft = Offset(bx, by + px * 0.75f),
                    size = androidx.compose.ui.geometry.Size(px, px * 0.25f),
                )
            }

            // crops: three stages, drawn as a small sprout that grows
            for ((x, y, _) in map.entries()) {
                val stage = cropsAt(x, y)
                if (stage <= 0) continue
                val cx = x * px - camera.x * scale + px / 2
                val cy = y * px - camera.y * scale + px / 2
                val h = (2 + stage * 2) * px / 16f
                drawRect(
                    color = Color(0xFF3F7A32),
                    topLeft = Offset(cx - px / 16f, cy - h),
                    size = androidx.compose.ui.geometry.Size(px / 8f, h),
                )
                drawRect(
                    color = Color(0xFF77A83F),
                    topLeft = Offset(cx - px / 4f, cy - h),
                    size = androidx.compose.ui.geometry.Size(px / 5f, px / 6f),
                )
            }

            // Night: paint the dark once, then punch holes where a torch burns.
            // Drawing the whole map twice (dark, then lit) would cost more than
            // the light is worth; a ring of clear pixels reads the same.
            if (nightAmount > 0.01f) {
                val firstVisibleCol = camera.x / GameMap.TILE
                val firstVisibleRow = camera.y / GameMap.TILE
                val visibleCols = (size.width / px).toInt() + 2
                val visibleRows = (size.height / px).toInt() + 2
                for (y in firstVisibleRow..(firstVisibleRow + visibleRows)) {
                    if (y < 0 || y >= map.rows) continue
                    for (x in firstVisibleCol..(firstVisibleCol + visibleCols)) {
                        if (x < 0 || x >= map.cols) continue
                        val sx = x * px - camera.x * scale
                        val sy = y * px - camera.y * scale
                        val alpha = if (litAt(x, y)) LIT_ALPHA * nightAmount else nightAmount * 0.62f
                        drawRect(
                            color = Color(0xFF0C1533).copy(alpha = alpha),
                            topLeft = Offset(sx, sy),
                            size = androidx.compose.ui.geometry.Size(px, px),
                        )
                    }
                }
            }
        }
    }
}

/** Over the lit cells the night is barely there; elsewhere it is a blue dusk. */
private const val LIT_ALPHA = 0.10f

private fun DrawScope.drawMap(
    map: GameMap,
    tiles: TileSet,
    atlas: ImageBitmap,
    camera: Camera,
    scale: Int,
    px: Float,
) {
    val firstCol = camera.x / GameMap.TILE
    val firstRow = camera.y / GameMap.TILE
    val cols = (size.width / px).toInt() + 2
    val rows = (size.height / px).toInt() + 2
    val lastCol = firstCol + cols
    val lastRow = firstRow + rows

    fun screenX(x: Int) = x * px - camera.x * scale
    fun screenY(y: Int) = y * px - camera.y * scale

    // Ground first for every visible cell, then buildings, then objects. Drawing
    // per cell instead would let the next cell's ground tile paint over the
    // overhang of a tall object, which is exactly the bug that turns a tree line
    // into a row of cut-off saplings.
    for (y in firstRow..lastRow) {
        if (y < 0 || y >= map.rows) continue
        for (x in firstCol..lastCol) {
            if (x < 0 || x >= map.cols) continue
            val cell = map.cell(x, y) ?: continue
            drawTile(tiles, atlas, cell.ground, screenX(x), screenY(y), px)
        }
    }
    for (y in firstRow..lastRow) {
        if (y < 0 || y >= map.rows) continue
        for (x in firstCol..lastCol) {
            if (x < 0 || x >= map.cols) continue
            val cell = map.cell(x, y) ?: continue
            drawTile(tiles, atlas, cell.building, screenX(x), screenY(y), px)
        }
    }
    for (y in firstRow..lastRow) {
        if (y < 0 || y >= map.rows) continue
        for (x in firstCol..lastCol) {
            if (x < 0 || x >= map.cols) continue
            val cell = map.cell(x, y) ?: continue
            drawTile(tiles, atlas, cell.objectTile, screenX(x), screenY(y), px)
        }
    }
}

private fun DrawScope.drawTile(
    tiles: TileSet,
    atlas: ImageBitmap,
    name: String?,
    screenX: Float,
    screenY: Float,
    px: Float,
) {
    if (name == null) return
    val tile = tiles[name] ?: return
    drawImage(
        image = atlas,
        srcOffset = androidx.compose.ui.unit.IntOffset(tile.x, tile.y),
        srcSize = androidx.compose.ui.unit.IntSize(tile.w, tile.h),
        dstOffset = androidx.compose.ui.unit.IntOffset(screenX.toInt(), screenY.toInt()),
        dstSize = androidx.compose.ui.unit.IntSize((tile.w * px / 16).toInt(), (tile.h * px / 16).toInt()),
        filterQuality = FilterQuality.None,
    )
}

/**
 * The player, from the walk sheet when it is loaded and from primitives if not.
 *
 * The fallback is not decoration: an atlas that failed to decode would otherwise
 * make the player vanish, and "where am I" is the one thing the screen must
 * always answer.
 */
private fun DrawScope.drawPlayer(
    x: Float,
    y: Float,
    px: Float,
    facing: Direction,
    stepParity: Boolean,
    walking: Boolean,
    sheet: ImageBitmap?,
) {
    if (sheet != null) {
        // The sheet already carries a left row, generated as a mirror of the
        // right one, so drawing is a plain blit: no runtime flip, no second
        // bitmap, and the frame lands on whole pixels like every tile.
        val column = PlayerSprite.column(walking, stepParity)
        val row = PlayerSprite.row(facing)
        drawImage(
            image = sheet,
            srcOffset = androidx.compose.ui.unit.IntOffset(
                PlayerSprite.frameX(column), PlayerSprite.frameY(row),
            ),
            srcSize = androidx.compose.ui.unit.IntSize(PlayerSprite.TILE, PlayerSprite.TILE),
            dstOffset = androidx.compose.ui.unit.IntOffset(x.toInt(), y.toInt()),
            dstSize = androidx.compose.ui.unit.IntSize(px.toInt(), px.toInt()),
            filterQuality = FilterQuality.None,
        )
        return
    }

    // Fallback silhouette: hat, face, body, feet, in the same proportions as
    // the sheet so the camera reads the same either way.
    val u = px / 16f
    drawRect(Color(0xFF2C2418), Offset(x + 4 * u, y + 2 * u), androidx.compose.ui.geometry.Size(8 * u, 3 * u))
    drawRect(Color(0xFFC53A2D), Offset(x + 3 * u, y + 3 * u), androidx.compose.ui.geometry.Size(10 * u, 2 * u))
    drawRect(Color(0xFFF2C79A), Offset(x + 5 * u, y + 5 * u), androidx.compose.ui.geometry.Size(6 * u, 3 * u))
    drawRect(Color(0xFF3E5C8A), Offset(x + 4 * u, y + 8 * u), androidx.compose.ui.geometry.Size(8 * u, 5 * u))
    drawRect(Color(0xFF2C2418), Offset(x + 4 * u, y + 13 * u), androidx.compose.ui.geometry.Size(3 * u, 2 * u))
    drawRect(Color(0xFF2C2418), Offset(x + 9 * u, y + 13 * u), androidx.compose.ui.geometry.Size(3 * u, 2 * u))
    // eyes follow the facing direction, the cheapest way to read intent
    val eyeY = y + 6 * u
    val leftEye = x + (if (facing == Direction.LEFT) 5.5f else 6.5f) * u
    drawRect(Color(0xFF2C2418), Offset(leftEye, eyeY), androidx.compose.ui.geometry.Size(u, u))
    if (facing != Direction.RIGHT) {
        drawRect(Color(0xFF2C2418), Offset(x + 9 * u, eyeY), androidx.compose.ui.geometry.Size(u, u))
    }
}
