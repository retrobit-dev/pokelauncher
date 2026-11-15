package dev.retrobit.pokelauncher.game

/**
 * Tap-to-move.
 *
 * You chose touch control, so the character has to find its own way: a tap
 * anywhere on the map walks there. Breadth-first search is the right tool on a
 * grid this size (160x100 worst case) and it returns the shortest path, so the
 * walk looks deliberate rather than drifting.
 *
 * When the tapped cell is solid, the walk stops on the nearest reachable cell
 * beside it. That single rule gives "walk up to a tree and chop it" for free.
 */
object Pathfinder {

    /** Safety valve: a 160x100 map is fine, a corrupt one should not hang. */
    const val MAX_VISITED = 40_000

    /**
     * Returns the cells to walk, excluding the start and including the goal.
     *
     * Empty when the goal is unreachable or is the cell you already stand on.
     */
    fun find(
        startX: Int,
        startY: Int,
        goalX: Int,
        goalY: Int,
        isWalkable: (Int, Int) -> Boolean,
    ): List<Pair<Int, Int>> {
        if (startX == goalX && startY == goalY) return emptyList()

        // Tapping a blocked cell means "get next to it", not "give up".
        val target = if (isWalkable(goalX, goalY)) {
            goalX to goalY
        } else {
            neighbours(goalX, goalY)
                // Prefer the neighbour closest to where the player stands, so a
                // tap on an adjacent tree does not send them around the pond to
                // reach it from the far side.
                .filter { (x, y) -> isWalkable(x, y) }
                .minByOrNull { (x, y) -> Math.abs(x - startX) + Math.abs(y - startY) }
                ?: return emptyList()
        }

        val width = 256 // generous key space; actual bounds come from isWalkable
        fun k(x: Int, y: Int): Int = (y + width) * width * 2 + (x + width)

        val cameFrom = HashMap<Int, Int>()
        val queue = ArrayDeque<Pair<Int, Int>>()
        val seen = HashSet<Int>()
        queue.add(startX to startY)
        seen.add(k(startX, startY))
        var visited = 0

        while (queue.isNotEmpty() && visited < MAX_VISITED) {
            val (cx, cy) = queue.removeFirst()
            visited++
            if (cx == target.first && cy == target.second) {
                return reconstruct(cameFrom, k(startX, startY), cx, cy)
            }
            for ((nx, ny) in neighbours(cx, cy)) {
                if (!isWalkable(nx, ny)) continue
                val nk = k(nx, ny)
                if (!seen.add(nk)) continue
                cameFrom[nk] = k(cx, cy)
                queue.addLast(nx to ny)
            }
        }
        return emptyList()
    }

    /** Orthogonal first, so a tie prefers the straight HeartGold walk. */
    private fun neighbours(x: Int, y: Int): List<Pair<Int, Int>> = listOf(
        x to (y + 1), x to (y - 1), (x - 1) to y, (x + 1) to y,
    )

    private fun reconstruct(
        cameFrom: Map<Int, Int>,
        startKey: Int,
        goalX: Int,
        goalY: Int,
    ): List<Pair<Int, Int>> {
        val width = 256
        fun k(x: Int, y: Int): Int = (y + width) * width * 2 + (x + width)
        val path = ArrayDeque<Pair<Int, Int>>()
        var current = k(goalX, goalY)
        val guard = MAX_VISITED
        var steps = 0
        while (current != startKey && steps++ < guard) {
            val x = current % (width * 2) - width
            val y = current / (width * 2) - width
            path.addFirst(x to y)
            current = cameFrom[current] ?: return emptyList()
        }
        return path.toList()
    }
}
