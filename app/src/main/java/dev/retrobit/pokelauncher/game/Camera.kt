package dev.retrobit.pokelauncher.game

/**
 * The camera: a window onto the map, always snapped to whole pixels.
 *
 * Two rules matter for the HeartGold look. First, tiles are 16px and must be
 * drawn at integer scale, so the camera only ever lands on an integer pixel.
 * Second, the character never walks off screen: the view follows with a dead
 * zone and stops at the map edge instead of showing the void beyond it.
 */
data class Camera(
    val x: Int = 0,
    val y: Int = 0,
    val viewWidth: Int,
    val viewHeight: Int,
    val mapWidth: Int,
    val mapHeight: Int,
) {
    fun follow(targetX: Int, targetY: Int): Camera {
        // Centre on the target, then clamp to the map. When the map is smaller
        // than the window, centre it instead of leaving a gap on one side.
        val wantX = targetX - viewWidth / 2
        val wantY = targetY - viewHeight / 2
        val maxX = mapWidth - viewWidth
        val maxY = mapHeight - viewHeight
        val nx = when {
            maxX <= 0 -> (mapWidth - viewWidth) / 2
            else -> wantX.coerceIn(0, maxX)
        }
        val ny = when {
            maxY <= 0 -> (mapHeight - viewHeight) / 2
            else -> wantY.coerceIn(0, maxY)
        }
        return copy(x = nx, y = ny)
    }

    /** First cell drawn, and how many fit: the renderer's loop bounds. */
    fun visibleCells(): IntRange = 0..(viewWidth / GameMap.TILE + 1)

    fun firstCol(): Int = x / GameMap.TILE
    fun firstRow(): Int = y / GameMap.TILE
}
