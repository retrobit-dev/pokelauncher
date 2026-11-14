package dev.retrobit.pokelauncher.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import dev.retrobit.pokelauncher.R

/**
 * Palette sampled from the HeartGold/SoulSilver UI: warm paper, dark coffee ink,
 * gold trim and the red of a Poké Ball. Everything is flat colour, no gradients
 * that look modern, because the DS look is paper flat.
 */
object HgColors {
    val Paper = Color(0xFFFBF3DC)
    val PaperDeep = Color(0xFFF3E4BF)
    val PaperShade = Color(0xFFE9D7AE)
    val Ink = Color(0xFF3B2F1E)
    val InkSoft = Color(0xFF6B5B44)
    val InkFaint = Color(0xFF9A8768)
    val Gold = Color(0xFFE0B84C)
    val GoldDeep = Color(0xFFC79A2E)
    val Red = Color(0xFFC53A2D)
    val RedDeep = Color(0xFF9A2A20)
    val Cream = Color(0xFFFFFBF0)
    val Shadow = Color(0x2E000000)
    val ScreenInk = Color(0xFF2C2418)

    // Johto landscape used when no wallpaper is shown.
    val SkyTop = Color(0xFF9FD4D2)
    val SkyBottom = Color(0xFFF4E7BE)
    val Sun = Color(0xFFF6E3A8)
    val Cloud = Color(0xFFFFFFFF)
    val HillFar = Color(0xFFAFC79A)
    val HillMid = Color(0xFF8FAF74)
    val HillNear = Color(0xFF7E9C63)
    val Grass = Color(0xFF5F7F4C)

    /** Cartridge shells for the six party slots: body + darker shade. */
    val cartridgeBodies = listOf(
        Color(0xFFE0B84C) to Color(0xFFC79A2E), // gold
        Color(0xFFC9CFD6) to Color(0xFFA5ADB7), // silver
        Color(0xFF8FB6D8) to Color(0xFF6F95B8), // crystal blue
        Color(0xFFD08070) to Color(0xFFB06152), // heart red
        Color(0xFF9DBB86) to Color(0xFF7D9B68), // leaf green
        Color(0xFFB7A0D4) to Color(0xFF977FB4), // dusk purple
    )

    fun cartridge(index: Int): Pair<Color, Color> =
        cartridgeBodies[((index % cartridgeBodies.size) + cartridgeBodies.size) % cartridgeBodies.size]
}

/** Press Start 2P: headings, clock, tiny caps labels. */
val PixelDisplay = FontFamily(Font(R.font.press_start_2p, FontWeight.Normal))

/** DotGothic16: pixel font with wide Latin + kana coverage, used for body text. */
val PixelBody = FontFamily(Font(R.font.dotgothic16, FontWeight.Normal))

/** Silkscreen: extra small labels, levels, counts. */
val PixelMono = FontFamily(Font(R.font.silkscreen, FontWeight.Normal))

object HgText {
    val display = TextStyle(
        fontFamily = PixelDisplay,
        fontSize = 11.sp,
        letterSpacing = 0.5.sp,
        color = HgColors.Ink,
    )
    val heading = TextStyle(
        fontFamily = PixelDisplay,
        fontSize = 8.sp,
        letterSpacing = 0.4.sp,
        color = HgColors.Ink,
    )
    val micro = TextStyle(
        fontFamily = PixelDisplay,
        fontSize = 6.sp,
        letterSpacing = 0.3.sp,
        color = HgColors.InkSoft,
    )
    val clock = TextStyle(
        fontFamily = PixelDisplay,
        fontSize = 13.sp,
        letterSpacing = 0.5.sp,
        color = HgColors.Ink,
    )
    val title = TextStyle(
        fontFamily = PixelBody,
        fontSize = 18.sp,
        color = HgColors.Ink,
    )
    val body = TextStyle(
        fontFamily = PixelBody,
        fontSize = 15.sp,
        color = HgColors.Ink,
    )
    val bodySoft = TextStyle(
        fontFamily = PixelBody,
        fontSize = 13.sp,
        color = HgColors.InkSoft,
    )
    val small = TextStyle(
        fontFamily = PixelBody,
        fontSize = 12.sp,
        color = HgColors.Ink,
    )
    val tiny = TextStyle(
        fontFamily = PixelMono,
        fontSize = 9.sp,
        color = HgColors.InkSoft,
    )
    val badge = TextStyle(
        fontFamily = PixelMono,
        fontSize = 10.sp,
        color = HgColors.Ink,
    )
}

private val HgColorScheme = lightColorScheme(
    primary = HgColors.GoldDeep,
    onPrimary = HgColors.Ink,
    secondary = HgColors.Red,
    onSecondary = HgColors.Cream,
    background = HgColors.Paper,
    onBackground = HgColors.Ink,
    surface = HgColors.Paper,
    onSurface = HgColors.Ink,
    surfaceVariant = HgColors.PaperDeep,
    onSurfaceVariant = HgColors.InkSoft,
    outline = HgColors.Ink,
)

private val HgTypography = Typography(
    displaySmall = HgText.display,
    headlineSmall = HgText.heading,
    titleLarge = HgText.title,
    bodyLarge = HgText.body,
    bodyMedium = HgText.bodySoft,
    labelSmall = HgText.tiny,
)

@Composable
fun PokeLauncherTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = HgColorScheme,
        typography = HgTypography,
        content = content,
    )
}
