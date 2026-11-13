package dev.retrobit.pokelauncher.game

/**
 * In-game time, on a real-time clock.
 *
 * The brief was "seperti dunia nyata": one in-game day is one real day, so the
 * sun in the app matches the sky outside at that moment. Nothing speeds up when
 * you look away, and nothing is lost while the app is killed; the clock is
 * derived from the wall clock, not accumulated from frames.
 *
 * That also means a session cannot "finish a day" by waiting, which is why
 * farming and building are the things worth doing minute to minute: crops grow
 * on real days, and the night period is the survival window.
 *
 * Pure Kotlin (no System.currentTimeMillis call inside): the caller passes the
 * time, so tests can stand at any hour.
 */
data class GameClock(
    /** Minutes since midnight, 0..1439. */
    val minuteOfDay: Int,
) {
    val hour: Int get() = minuteOfDay / 60
    val minute: Int get() = minuteOfDay % 60

    /** 06:00-17:59 daylight, 18:00-05:59 night. */
    val isNight: Boolean get() = hour < 6 || hour >= 18

    /** 0.0 at night, 1.0 at noon: drives the light overlay. */
    val daylight: Float
        get() {
            val m = minuteOfDay
            return when {
                m <= 240 -> 0f                       // 00:00-04:00 full dark
                m < 360 -> (m - 240) / 120f          // dawn ramp 04:00-06:00
                m < 1080 -> 1f                       // 06:00-18:00 full day
                m < 1200 -> 1f - (m - 1080) / 120f   // dusk 18:00-20:00
                else -> 0f
            }
        }

    /** "18:42" for the HUD. */
    fun label(): String = "%02d:%02d".format(hour, minute)

    companion object {
        const val MINUTES_PER_DAY = 24 * 60

        fun atMinute(minuteOfDay: Int): GameClock =
            GameClock(((minuteOfDay % MINUTES_PER_DAY) + MINUTES_PER_DAY) % MINUTES_PER_DAY)

        fun fromMillisUtc(epochMillis: Long, utcOffsetMinutes: Int): GameClock {
            val shifted = epochMillis + utcOffsetMinutes * 60_000L
            val minutesOfDay = ((shifted / 60_000L) % MINUTES_PER_DAY).toInt()
            return atMinute(minutesOfDay)
        }
    }
}
