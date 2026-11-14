package dev.retrobit.pokelauncher.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import dev.retrobit.pokelauncher.BuildConfig
import dev.retrobit.pokelauncher.R
import dev.retrobit.pokelauncher.data.CardStyle
import dev.retrobit.pokelauncher.data.LauncherSettings
import dev.retrobit.pokelauncher.ui.components.CloseIcon
import dev.retrobit.pokelauncher.ui.components.HgButton
import dev.retrobit.pokelauncher.ui.components.HgIconButton
import dev.retrobit.pokelauncher.ui.components.HgPanel
import dev.retrobit.pokelauncher.ui.components.Pokeball
import dev.retrobit.pokelauncher.ui.theme.HgColors
import dev.retrobit.pokelauncher.ui.theme.HgText

/**
 * Settings styled as the HeartGold options menu: paper panel, gold section
 * headers and chunky toggle chips.
 */
@Composable
fun SettingsScreen(
    settings: LauncherSettings,
    onColumnsChange: (Int) -> Unit,
    onShowClockChange: (Boolean) -> Unit,
    onCardStyleChange: (CardStyle) -> Unit,
    onSetDefaultHome: () -> Unit,
    onClose: () -> Unit,
) {
    // Kept for API compatibility with older call sites; the launcher now shows
    // settings inline next to the party grid via [SettingsContent].
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(HgColors.Paper.copy(alpha = 0.98f))
            .safeDrawingPadding(),
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 10.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Pokeball(size = 22.dp)
                Spacer(Modifier.width(8.dp))
                Text(text = stringResource(R.string.settings_title), style = HgText.display)
                Spacer(Modifier.weight(1f))
                HgIconButton(
                    onClick = onClose,
                    contentDescription = stringResource(R.string.settings_close),
                    size = 40.dp,
                ) {
                    CloseIcon(size = 16.dp)
                }
            }
            Spacer(Modifier.height(14.dp))
            SettingsContent(
                settings = settings,
                onColumnsChange = onColumnsChange,
                onShowClockChange = onShowClockChange,
                onCardStyleChange = onCardStyleChange,
                onSetDefaultHome = onSetDefaultHome,
            )
        }
    }
}

/**
 * The settings form itself, without the full screen chrome, so it can be shown
 * inline next to the home screen content on tablets and foldables.
 */
@Composable
fun SettingsContent(
    settings: LauncherSettings,
    onColumnsChange: (Int) -> Unit,
    onShowClockChange: (Boolean) -> Unit,
    onCardStyleChange: (CardStyle) -> Unit,
    onSetDefaultHome: () -> Unit,
) {
    Column {
        SectionHeader(stringResource(R.string.settings_section_home))
        HgPanel(modifier = Modifier.fillMaxWidth(), contentPadding = 14.dp) {
            Column {
                Text(text = stringResource(R.string.settings_set_default), style = HgText.body)
                Spacer(Modifier.height(4.dp))
                Text(
                    text = stringResource(R.string.settings_set_default_desc),
                    style = HgText.bodySoft,
                )
                Spacer(Modifier.height(10.dp))
                HgButton(
                    text = stringResource(R.string.settings_set_default_action),
                    onClick = onSetDefaultHome,
                    fill = HgColors.PaperDeep,
                )
            }
        }

        Spacer(Modifier.height(14.dp))
        SectionHeader(stringResource(R.string.settings_section_look))
        HgPanel(modifier = Modifier.fillMaxWidth(), contentPadding = 14.dp) {
            Column {
                ToggleRow(
                    title = stringResource(R.string.settings_hide_clock),
                    subtitle = stringResource(R.string.settings_hide_clock_desc),
                    checked = settings.showClock,
                    onCheckedChange = onShowClockChange,
                )
                Divider()
                Text(text = stringResource(R.string.settings_columns), style = HgText.body)
                Spacer(Modifier.height(8.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    LauncherSettings.COLUMN_CHOICES.forEach { columns ->
                        ChoiceChip(
                            text = stringResource(R.string.settings_columns_value, columns),
                            selected = settings.columns == columns,
                            onClick = { onColumnsChange(columns) },
                        )
                    }
                }
                Divider()
                Text(text = stringResource(R.string.settings_layout), style = HgText.body)
                Spacer(Modifier.height(8.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    ChoiceChip(
                        text = stringResource(R.string.settings_layout_cartridge),
                        selected = settings.cardStyle == CardStyle.Cartridge,
                        onClick = { onCardStyleChange(CardStyle.Cartridge) },
                    )
                    ChoiceChip(
                        text = stringResource(R.string.settings_layout_tile),
                        selected = settings.cardStyle == CardStyle.Tile,
                        onClick = { onCardStyleChange(CardStyle.Tile) },
                    )
                }
            }
        }

        Spacer(Modifier.height(14.dp))
        SectionHeader(stringResource(R.string.settings_section_about))
        HgPanel(modifier = Modifier.fillMaxWidth(), contentPadding = 14.dp) {
            Column {
                Text(
                    text = stringResource(R.string.settings_version, BuildConfig.VERSION_NAME),
                    style = HgText.body,
                )
                Spacer(Modifier.height(4.dp))
                Text(
                    text = stringResource(R.string.settings_note),
                    style = HgText.bodySoft,
                )
                Spacer(Modifier.height(8.dp))
                Text(text = stringResource(R.string.settings_fonts), style = HgText.tiny)
            }
        }
        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun SectionHeader(text: String) {
    Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
        Text(text = text, style = HgText.micro.copy(color = HgColors.RedDeep))
        Spacer(Modifier.width(8.dp))
        Box(
            modifier = Modifier
                .weight(1f)
                .height(1.dp)
                .background(HgColors.Gold),
        )
    }
    Spacer(Modifier.height(8.dp))
}

@Composable
private fun Divider() {
    Spacer(Modifier.height(12.dp))
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(1.dp)
            .background(HgColors.InkFaint.copy(alpha = 0.35f)),
    )
    Spacer(Modifier.height(12.dp))
}

@Composable
private fun ToggleRow(
    title: String,
    subtitle: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit,
) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Column(modifier = Modifier.weight(1f)) {
            Text(text = title, style = HgText.body)
            Spacer(Modifier.height(2.dp))
            Text(text = subtitle, style = HgText.tiny)
        }
        Spacer(Modifier.width(12.dp))
        HgToggle(checked = checked, onCheckedChange = onCheckedChange)
    }
}

/** A pixel art switch: a small track with a Poké Ball as the thumb. */
@Composable
private fun HgToggle(checked: Boolean, onCheckedChange: (Boolean) -> Unit) {
    Box(
        modifier = Modifier
            .size(width = 58.dp, height = 30.dp)
            .clip(RoundedCornerShape(15.dp))
            .background(if (checked) HgColors.Gold else HgColors.PaperShade)
            .border(2.dp, HgColors.Ink, RoundedCornerShape(15.dp))
            .clickable { onCheckedChange(!checked) }
            .padding(3.dp),
    ) {
        Box(
            modifier = Modifier
                .align(if (checked) Alignment.CenterEnd else Alignment.CenterStart)
                .size(22.dp)
                .clip(CircleShape)
                .background(HgColors.Paper),
            contentAlignment = Alignment.Center,
        ) {
            Pokeball(size = 16.dp)
        }
    }
}

@Composable
private fun ChoiceChip(text: String, selected: Boolean, onClick: () -> Unit) {
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(9.dp))
            .background(if (selected) HgColors.Gold else HgColors.Cream)
            .border(
                width = 2.dp,
                color = if (selected) HgColors.Ink else HgColors.InkFaint.copy(alpha = 0.6f),
                shape = RoundedCornerShape(9.dp),
            )
            .clickable(onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 8.dp),
    ) {
        Text(
            text = text,
            style = HgText.small.copy(color = if (selected) HgColors.Ink else HgColors.InkSoft),
        )
    }
}
