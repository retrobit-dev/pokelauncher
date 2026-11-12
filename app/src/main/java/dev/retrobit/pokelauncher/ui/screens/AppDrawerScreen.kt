package dev.retrobit.pokelauncher.ui.screens

import android.graphics.drawable.Drawable
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import dev.retrobit.pokelauncher.R
import dev.retrobit.pokelauncher.data.AppEntry
import dev.retrobit.pokelauncher.data.PartySlot
import dev.retrobit.pokelauncher.ui.components.AppIcon
import dev.retrobit.pokelauncher.ui.components.CloseIcon
import dev.retrobit.pokelauncher.ui.components.SearchIcon
import dev.retrobit.pokelauncher.ui.components.HgIconButton
import dev.retrobit.pokelauncher.ui.components.HgInset
import dev.retrobit.pokelauncher.ui.components.Pokeball
import dev.retrobit.pokelauncher.ui.components.rememberAppIcon
import dev.retrobit.pokelauncher.ui.theme.HgColors
import dev.retrobit.pokelauncher.ui.theme.HgText

/**
 * Full screen app list, styled as a DS storage box: search field, grid of apps,
 * quick party toggle and long press for app details.
 */
@Composable
fun AppDrawerScreen(
    apps: List<AppEntry>,
    party: List<PartySlot>,
    iconFor: (AppEntry) -> Drawable?,
    onLaunch: (AppEntry) -> Unit,
    onToggleParty: (AppEntry) -> Unit,
    onAppInfo: (AppEntry) -> Unit,
    onClose: () -> Unit,
) {
    var query by rememberSaveable { mutableStateOf("") }
    val partyKeys = remember(party) { party.map { it.key }.toSet() }
    val filtered = remember(apps, query) {
        if (query.isBlank()) apps else apps.filter { it.label.contains(query, ignoreCase = true) }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(HgColors.Paper.copy(alpha = 0.98f))
            .safeDrawingPadding(),
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 16.dp, vertical = 10.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Pokeball(size = 22.dp)
                Spacer(Modifier.width(8.dp))
                Text(text = stringResource(R.string.drawer_title), style = HgText.display)
                Spacer(Modifier.weight(1f))
                HgIconButton(
                    onClick = onClose,
                    contentDescription = stringResource(R.string.drawer_close),
                    size = 40.dp,
                ) {
                    CloseIcon(size = 16.dp)
                }
            }
            Spacer(Modifier.height(10.dp))
            SearchField(
                value = query,
                onValueChange = { query = it },
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(6.dp))
            Text(
                text = stringResource(R.string.drawer_count, filtered.size),
                style = HgText.tiny,
                modifier = Modifier.padding(start = 2.dp),
            )
            Spacer(Modifier.height(8.dp))

            if (filtered.isEmpty()) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text(
                        text = stringResource(
                            if (apps.isEmpty()) R.string.drawer_loading else R.string.drawer_empty,
                        ),
                        style = HgText.bodySoft,
                    )
                }
            } else {
                LazyVerticalGrid(
                    columns = GridCells.Fixed(4),
                    contentPadding = PaddingValues(bottom = 16.dp),
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    items(items = filtered, key = { it.key }) { entry ->
                        DrawerTile(
                            entry = entry,
                            inParty = entry.key in partyKeys,
                            iconFor = iconFor,
                            onLaunch = { onLaunch(entry) },
                            onToggleParty = { onToggleParty(entry) },
                            onAppInfo = { onAppInfo(entry) },
                        )
                    }
                    item(span = { GridItemSpan(maxLineSpan) }) {
                        Text(
                            text = stringResource(R.string.drawer_help),
                            style = HgText.tiny,
                            modifier = Modifier.padding(top = 8.dp),
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun SearchField(
    value: String,
    onValueChange: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    HgInset(modifier = modifier, fill = HgColors.Cream) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            SearchIcon(size = 16.dp)
            Spacer(Modifier.width(8.dp))
            Box(modifier = Modifier.weight(1f)) {
                if (value.isEmpty()) {
                    Text(text = stringResource(R.string.drawer_search_hint), style = HgText.bodySoft)
                }
                BasicTextField(
                    value = value,
                    onValueChange = onValueChange,
                    singleLine = true,
                    textStyle = HgText.body.copy(color = HgColors.Ink),
                    cursorBrush = SolidColor(HgColors.Red),
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
                    modifier = Modifier.fillMaxWidth(),
                )
            }
            if (value.isNotEmpty()) {
                Box(
                    modifier = Modifier
                        .size(22.dp)
                        .clip(CircleShape)
                        .background(HgColors.PaperShade)
                        .clickable { onValueChange("") },
                    contentAlignment = Alignment.Center,
                ) {
                    CloseIcon(size = 11.dp, strokeWidth = 1.5.dp)
                }
            }
        }
    }
}

@Composable
private fun DrawerTile(
    entry: AppEntry,
    inParty: Boolean,
    iconFor: (AppEntry) -> Drawable?,
    onLaunch: () -> Unit,
    onToggleParty: () -> Unit,
    onAppInfo: () -> Unit,
) {
    val icon = rememberAppIcon(entry, iconFor)

    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(12.dp))
                .background(if (inParty) HgColors.PaperDeep else HgColors.Cream)
                .border(
                    width = if (inParty) 2.dp else 1.dp,
                    color = if (inParty) HgColors.GoldDeep else HgColors.InkFaint.copy(alpha = 0.5f),
                    shape = RoundedCornerShape(12.dp),
                )
                .combinedClickable(
                    interactionSource = remember { MutableInteractionSource() },
                    indication = null,
                    onClick = onLaunch,
                    onLongClick = onAppInfo,
                )
                .padding(8.dp),
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(52.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    if (icon != null) {
                        AppIcon(icon = icon, label = entry.label, size = 44.dp)
                    } else {
                        Text(text = entry.label.take(1).uppercase(), style = HgText.title)
                    }
                }
                Spacer(Modifier.height(4.dp))
                Text(
                    text = entry.label,
                    style = HgText.small,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Spacer(Modifier.height(4.dp))
                Box(
                    modifier = Modifier
                        .size(28.dp)
                        .clip(CircleShape)
                        .clickable { onToggleParty() },
                    contentAlignment = Alignment.Center,
                ) {
                    if (inParty) {
                        Pokeball(size = 19.dp)
                    } else {
                        Box(
                            modifier = Modifier
                                .size(19.dp)
                                .clip(CircleShape)
                                .border(1.5.dp, HgColors.InkFaint, CircleShape),
                        )
                    }
                }
            }
        }
    }
}
