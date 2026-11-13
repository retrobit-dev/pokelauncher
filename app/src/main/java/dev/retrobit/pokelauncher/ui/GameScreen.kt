package dev.retrobit.pokelauncher.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
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
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.WindowInsetsSides
import androidx.compose.foundation.layout.displayCutout
import androidx.compose.foundation.layout.only
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.retrobit.pokelauncher.game.GameClock
import dev.retrobit.pokelauncher.ui.theme.HgColors
import dev.retrobit.pokelauncher.ui.theme.HgText
import kotlinx.coroutines.delay

/**
 * The in-world HUD: clock and vitals top-left, the launcher machine prompt
 * bottom-right when you stand beside it.
 *
 * All of it is drawn on top of the map rather than beside it, because the map is
 * meant to fill the tablet. The panels use the same paper-and-ink palette as the
 * rest of the launcher, so the game does not look like a different app.
 */
@Composable
fun GameHud(
    clock: GameClock,
    health: Int,
    maxHealth: Int,
    hunger: Int,
    maxHunger: Int,
    wood: Int,
    stone: Int,
    food: Int,
    seeds: Int,
    nearMachine: Boolean,
    message: String?,
    messageId: Int,
    onOpenLauncher: () -> Unit,
    onOpenMenu: () -> Unit,
    onEat: () -> Unit,
    onTill: () -> Unit,
    onPlaceLight: () -> Unit,
    modifier: Modifier = Modifier,
) {
    // A tapped tree must answer immediately, or the world feels dead. The
    // message is state, the timer only decides when to stop drawing it.
    var visible by remember { mutableStateOf<String?>(null) }
    LaunchedEffect(messageId) {
        visible = message
        if (message != null) {
            delay(2_200L)
            visible = null
        }
    }

    // The MatePad Mini puts its camera inside the panel, top-left in landscape.
    // Without this the clock would sit under the lens, which is exactly the bug
    // the device render showed before the HUD learned about the cutout.
    Box(
        modifier = modifier
            .fillMaxSize()
            .windowInsetsPadding(
                WindowInsets.displayCutout.only(WindowInsetsSides.Top + WindowInsetsSides.Start),
            ),
    ) {
        Column(
            modifier = Modifier
                .align(Alignment.TopStart)
                .padding(12.dp)
                .clip(RoundedCornerShape(10.dp))
                .background(HgColors.Paper.copy(alpha = 0.94f))
                .border(2.dp, HgColors.Ink, RoundedCornerShape(10.dp))
                .padding(horizontal = 10.dp, vertical = 8.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(text = clock.label(), style = HgText.display, color = HgColors.Ink)
                Spacer(Modifier.width(8.dp))
                Text(
                    text = if (clock.isNight) "MALAM" else "SIANG",
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Bold,
                    color = if (clock.isNight) HgColors.Red else HgColors.GoldDeep,
                )
            }
            Spacer(Modifier.height(4.dp))
            VitalRow(label = "NYAWA", current = health, max = maxHealth, colour = HgColors.Red)
            VitalRow(label = "LAPAR", current = hunger, max = maxHunger, colour = HgColors.GoldDeep)
            Spacer(Modifier.height(4.dp))
            Text(
                text = "kayu $wood  batu $stone  bibit $seeds  makanan $food",
                fontSize = 11.sp,
                color = HgColors.InkSoft,
                fontWeight = FontWeight.Medium,
            )
        }

        // Top-right: the way into settings and the app list. It has to live in
        // the world, because the world is the whole home screen: without this
        // the menu sheet can never open.
        Box(
            modifier = Modifier
                .align(Alignment.TopEnd)
                .padding(12.dp)
                .size(44.dp)
                .clip(RoundedCornerShape(10.dp))
                .background(HgColors.Paper.copy(alpha = 0.94f))
                .border(2.dp, HgColors.Ink, RoundedCornerShape(10.dp))
                .clickable { onOpenMenu() },
            contentAlignment = Alignment.Center,
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
                repeat(3) {
                    Box(
                        modifier = Modifier
                            .size(width = 18.dp, height = 2.dp)
                            .background(HgColors.Ink),
                    )
                }
            }
        }

        // bottom-left: verb buttons, one tap each, no modifier keys on a tablet
        Row(
            modifier = Modifier
                .align(Alignment.BottomStart)
                .padding(12.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            VerbButton(label = "TANAM", enabled = true, onClick = onTill)
            VerbButton(label = "MAKAN", enabled = food > 0, onClick = onEat)
            VerbButton(label = "LAMPU", enabled = true, onClick = onPlaceLight)
        }

        visible?.let { line ->
            Column(
                modifier = Modifier
                    .align(Alignment.TopCenter)
                    .padding(top = 12.dp)
                    .clip(RoundedCornerShape(10.dp))
                    .background(HgColors.Paper.copy(alpha = 0.96f))
                    .border(2.dp, HgColors.Gold, RoundedCornerShape(10.dp))
                    .padding(horizontal = 12.dp, vertical = 7.dp),
            ) {
                Text(text = line, fontSize = 12.sp, fontWeight = FontWeight.Bold, color = HgColors.Ink)
            }
        }

        if (nearMachine) {
            Row(
                modifier = Modifier
                    .align(Alignment.BottomEnd)
                    .padding(12.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(HgColors.Paper)
                    .border(3.dp, HgColors.Gold, RoundedCornerShape(12.dp))
                    .clickable { onOpenLauncher() }
                    .padding(horizontal = 14.dp, vertical = 10.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Box(
                    modifier = Modifier
                        .size(30.dp)
                        .clip(RoundedCornerShape(6.dp))
                        .background(HgColors.ScreenInk)
                        .border(2.dp, HgColors.InkSoft, RoundedCornerShape(6.dp)),
                )
                Spacer(Modifier.width(10.dp))
                Column {
                    Text(text = "MESIN LAUNCHER", style = HgText.display, fontSize = 12.sp)
                    Text(text = "ketuk untuk buka aplikasi", fontSize = 11.sp, color = HgColors.InkSoft)
                }
            }
        }
    }
}

@Composable
private fun VerbButton(label: String, enabled: Boolean, onClick: () -> Unit) {
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(10.dp))
            .background(if (enabled) HgColors.Paper else HgColors.PaperShade)
            .border(2.dp, HgColors.Ink, RoundedCornerShape(10.dp))
            .clickable(enabled = enabled) { onClick() }
            .padding(horizontal = 12.dp, vertical = 8.dp),
    ) {
        Text(
            text = label,
            fontSize = 11.sp,
            fontWeight = FontWeight.Bold,
            color = if (enabled) HgColors.Ink else HgColors.InkFaint,
        )
    }
}

@Composable
private fun VitalRow(label: String, current: Int, max: Int, colour: Color) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Text(
            text = label,
            fontSize = 9.sp,
            color = HgColors.InkFaint,
            modifier = Modifier.width(40.dp),
            fontWeight = FontWeight.Bold,
        )
        Row(horizontalArrangement = Arrangement.spacedBy(2.dp)) {
            repeat(max) { index ->
                Box(
                    modifier = Modifier
                        .size(width = 8.dp, height = 8.dp)
                        .background(if (index < current) colour else HgColors.PaperShade),
                )
            }
        }
    }
}

/** Keeps a [GameClock] in step with the device clock, one tick per minute. */
@Composable
fun rememberRealClock(utcOffsetMinutes: Int): GameClock {
    var clock by remember { mutableStateOf(GameClock.atMinute(12 * 60)) }
    LaunchedEffect(utcOffsetMinutes) {
        while (true) {
            clock = GameClock.fromMillisUtc(System.currentTimeMillis(), utcOffsetMinutes)
            delay(30_000L)
        }
    }
    return clock
}
