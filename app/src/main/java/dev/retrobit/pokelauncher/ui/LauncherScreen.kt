package dev.retrobit.pokelauncher.ui

import android.graphics.drawable.Drawable
import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.itemsIndexed
import androidx.compose.foundation.lazy.grid.rememberLazyGridState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import dev.retrobit.pokelauncher.data.AppEntry
import dev.retrobit.pokelauncher.data.LauncherSettings
import dev.retrobit.pokelauncher.data.LauncherUiState
import dev.retrobit.pokelauncher.data.PartySlot
import dev.retrobit.pokelauncher.ui.components.CloseIcon
import dev.retrobit.pokelauncher.ui.components.GearIcon
import dev.retrobit.pokelauncher.ui.components.HgButton
import dev.retrobit.pokelauncher.ui.components.HgIconButton
import dev.retrobit.pokelauncher.ui.components.HgPanel
import dev.retrobit.pokelauncher.ui.components.JohtoWallpaper
import dev.retrobit.pokelauncher.ui.components.MenuIcon
import dev.retrobit.pokelauncher.ui.components.MiniDiorama
import dev.retrobit.pokelauncher.ui.components.PartyIndicator
import dev.retrobit.pokelauncher.ui.components.PartySlotCard
import dev.retrobit.pokelauncher.ui.components.rememberAppIcon
import dev.retrobit.pokelauncher.ui.components.Pokeball
import dev.retrobit.pokelauncher.ui.screens.AppDrawerScreen
import dev.retrobit.pokelauncher.ui.screens.AppInfoSheet
import dev.retrobit.pokelauncher.ui.screens.HgDialog
import dev.retrobit.pokelauncher.ui.screens.MenuSheet
import dev.retrobit.pokelauncher.ui.screens.SettingsContent
import dev.retrobit.pokelauncher.ui.screens.SettingsScreen
import dev.retrobit.pokelauncher.ui.theme.HgColors
import dev.retrobit.pokelauncher.ui.theme.HgText
import dev.retrobit.pokelauncher.R
import java.time.LocalTime
import java.time.format.DateTimeFormatter
import kotlinx.coroutines.delay

/**
 * Root composable: wallpaper, party grid, clock widget and the modal layers
 * (drawer, settings, menu, sheet). Modals are plain Compose state so Back
 * handling stays explicit and predictable.
 */
@Composable
fun LauncherScreen(viewModel: LauncherViewModel) {
    val state by viewModel.state.collectAsState()
    val settings = state.settings

    var showDrawer by rememberSaveable { mutableStateOf(false) }
    var showSettings by rememberSaveable { mutableStateOf(false) }
    var showMenu by rememberSaveable { mutableStateOf(false) }
    var selectedApp by remember { mutableStateOf<AppEntry?>(null) }
    var showSetDefaultDialog by rememberSaveable { mutableStateOf(false) }
    var showPartyFullDialog by rememberSaveable { mutableStateOf(false) }

    // Exactly one BackHandler is registered, so the topmost layer always wins.
    // With no layer open the press is swallowed: a HOME activity must never
    // blank the screen or fall through to the previous activity.
    BackHandler(enabled = true) {
        when {
            showPartyFullDialog -> showPartyFullDialog = false
            showSetDefaultDialog -> showSetDefaultDialog = false
            selectedApp != null -> selectedApp = null
            showMenu -> showMenu = false
            showDrawer -> showDrawer = false
            showSettings -> showSettings = false
            else -> Unit
        }
    }

    val wideLayout = LocalConfiguration.current.screenWidthDp >= 700

    Box(modifier = Modifier.fillMaxSize()) {
        Row(modifier = Modifier.fillMaxSize()) {
            // Home content: wallpaper, top bar, player card and the party grid.
            Box(modifier = Modifier.weight(1f)) {
                HomeSurface(
                    state = state,
                    settings = settings,
                    onOpenDrawer = { showDrawer = true },
                    onOpenMenu = { showMenu = true },
                    onOpenSettings = { showSettings = true },
                    onAddFavourite = { showDrawer = true },
                    onLaunchSlot = { slot ->
                        launchSlot(viewModel, slot, onMissing = { showDrawer = true })
                    },
                    onSlotLongPress = { slot ->
                        if (slot.installed) {
                            state.apps.firstOrNull { it.key == slot.key }?.let { selectedApp = it }
                        } else {
                            viewModel.removeFromParty(slot.key)
                        }
                    },
                    iconProvider = viewModel::iconFor,
                )
            }

            // On tablets and foldables the settings slide in as a side panel so
            // the party stays visible; on phones they take over the screen.
            if (wideLayout) {
                AnimatedVisibility(
                    visible = showSettings,
                    enter = fadeIn(),
                    exit = fadeOut(),
                ) {
                    Box(
                        modifier = Modifier
                            .fillMaxHeight()
                            .width(380.dp)
                            .background(HgColors.Paper),
                    ) {
                        Column(
                            modifier = Modifier
                                .fillMaxSize()
                                .statusBarsPadding()
                                .navigationBarsPadding()
                                .verticalScroll(rememberScrollState())
                                .padding(16.dp),
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Text(text = stringResource(R.string.settings_title), style = HgText.display)
                                Spacer(Modifier.weight(1f))
                                HgIconButton(
                                    onClick = { showSettings = false },
                                    contentDescription = stringResource(R.string.settings_close),
                                    size = 36.dp,
                                ) {
                                    CloseIcon(size = 16.dp)
                                }
                            }
                            Spacer(Modifier.height(12.dp))
                            SettingsContent(
                                settings = settings,
                                onColumnsChange = viewModel::setColumns,
                                onShowClockChange = viewModel::setShowClock,
                                onCardStyleChange = viewModel::setCardStyle,
                                onSetDefaultHome = { showSetDefaultDialog = true },
                            )
                        }
                    }
                }
            }
        }

        AnimatedVisibility(
            visible = showDrawer,
            enter = fadeIn() + slideInVertically { it / 8 },
            exit = fadeOut() + slideOutVertically { it / 8 },
        ) {
            AppDrawerScreen(
                apps = state.apps,
                party = state.party,
                iconFor = viewModel::iconFor,
                onLaunch = { entry ->
                    if (!viewModel.launch(entry)) selectedApp = entry
                },
                onToggleParty = { entry ->
                    val changed = viewModel.toggleParty(entry.key)
                    if (!changed && viewModel.isPartyFull()) showPartyFullDialog = true
                },
                onAppInfo = { entry -> selectedApp = entry },
                onClose = { showDrawer = false },
            )
        }

        AnimatedVisibility(
            visible = showSettings && !wideLayout,
            enter = fadeIn() + slideInVertically { it / 10 },
            exit = fadeOut() + slideOutVertically { it / 10 },
        ) {
            SettingsScreen(
                settings = settings,
                onColumnsChange = viewModel::setColumns,
                onShowClockChange = viewModel::setShowClock,
                onCardStyleChange = viewModel::setCardStyle,
                onSetDefaultHome = { showSetDefaultDialog = true },
                onClose = { showSettings = false },
            )
        }

        MenuSheet(
            visible = showMenu,
            onDismiss = { showMenu = false },
            onAllApps = {
                showMenu = false
                showDrawer = true
            },
            onSettings = {
                showMenu = false
                showSettings = true
            },
            onSetDefault = {
                showMenu = false
                showSetDefaultDialog = true
            },
        )

        AppInfoSheet(
            entry = selectedApp,
            isFavourite = selectedApp?.let { state.isInParty(it.key) } ?: false,
            icon = rememberAppIcon(selectedApp, viewModel::iconFor),
            onDismiss = { selectedApp = null },
            onOpen = { entry ->
                viewModel.launch(entry)
                selectedApp = null
            },
            onAppInfo = { entry ->
                viewModel.openAppInfo(entry.packageName)
                selectedApp = null
            },
            onUninstall = { entry ->
                viewModel.uninstall(entry.packageName)
                selectedApp = null
            },
            onToggleFavourite = { entry ->
                val wasFavourite = state.isInParty(entry.key)
                val changed = viewModel.toggleParty(entry.key)
                if (!changed && !wasFavourite) showPartyFullDialog = true
                if (wasFavourite) selectedApp = null
            },
        )

        if (showSetDefaultDialog) {
            HgDialog(
                title = stringResource(R.string.dialog_set_default_title),
                body = stringResource(R.string.dialog_set_default_body),
                confirmLabel = stringResource(R.string.dialog_open_settings),
                dismissLabel = stringResource(R.string.dialog_cancel),
                onConfirm = {
                    showSetDefaultDialog = false
                    if (!viewModel.openHomeSettings()) {
                        // Some ROMs hide the HOME settings page; fall back to app details.
                        viewModel.openAppInfo(DEFAULT_APP_INFO_PACKAGE)
                    }
                },
                onDismiss = { showSetDefaultDialog = false },
            )
        }

        if (showPartyFullDialog) {
            HgDialog(
                title = stringResource(R.string.dialog_party_full_title),
                body = stringResource(R.string.dialog_party_full_body),
                confirmLabel = stringResource(R.string.dialog_ok),
                onConfirm = { showPartyFullDialog = false },
                onDismiss = { showPartyFullDialog = false },
            )
        }
    }
}

private const val DEFAULT_APP_INFO_PACKAGE = "dev.retrobit.pokelauncher"

private fun launchSlot(viewModel: LauncherViewModel, slot: PartySlot, onMissing: () -> Unit) {
    if (!slot.installed) {
        onMissing()
        return
    }
    viewModel.launch(
        AppEntry(
            packageName = slot.packageName,
            activityName = slot.activityName,
            label = slot.label,
        )
    )
}

@Composable
private fun HomeSurface(
    state: LauncherUiState,
    settings: LauncherSettings,
    onOpenDrawer: () -> Unit,
    onOpenMenu: () -> Unit,
    onOpenSettings: () -> Unit,
    onAddFavourite: () -> Unit,
    onLaunchSlot: (PartySlot) -> Unit,
    onSlotLongPress: (PartySlot) -> Unit,
    iconProvider: (AppEntry) -> Drawable?,
) {
    Box(modifier = Modifier.fillMaxSize()) {
        JohtoWallpaper(modifier = Modifier.fillMaxSize())

        // Paper scrim: keeps text readable over the illustration without turning
        // the wallpaper into mush.
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(
                    Brush.verticalGradient(
                        0f to Color.White.copy(alpha = 0.28f),
                        0.42f to Color.Transparent,
                        0.74f to HgColors.Paper.copy(alpha = 0.22f),
                        1f to HgColors.Paper.copy(alpha = 0.60f),
                    )
                )
        )

        Column(
            modifier = Modifier
                .fillMaxSize()
                .safeDrawingPadding()
                .padding(horizontal = 16.dp, vertical = 10.dp),
        ) {
            TopBar(
                showClock = settings.showClock,
                onOpenMenu = onOpenMenu,
                onOpenSettings = onOpenSettings,
            )
            Spacer(Modifier.height(10.dp))
            PlayerCard(partyCount = state.party.size, onOpenDrawer = onOpenDrawer)
            Spacer(Modifier.height(10.dp))
            PartyGrid(
                state = state,
                settings = settings,
                modifier = Modifier.weight(1f),
                onLaunchSlot = onLaunchSlot,
                onSlotLongPress = onSlotLongPress,
                onAddFavourite = onAddFavourite,
                iconProvider = iconProvider,
            )
        }
    }
}

@Composable
private fun TopBar(
    showClock: Boolean,
    onOpenMenu: () -> Unit,
    onOpenSettings: () -> Unit,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (showClock) {
            ClockBadge()
        } else {
            HgIconButton(
                onClick = onOpenMenu,
                contentDescription = stringResource(R.string.top_menu),
                size = 42.dp,
            ) {
                MenuIcon(size = 18.dp)
            }
        }
        Spacer(Modifier.weight(1f))
        HgIconButton(
            onClick = onOpenSettings,
            contentDescription = stringResource(R.string.top_settings),
        ) {
            GearIcon(size = 20.dp)
        }
    }
}

@Composable
private fun ClockBadge() {
    var timeText by remember { mutableStateOf(formatNow()) }
    LaunchedEffect(Unit) {
        while (true) {
            // Sleep exactly until the next minute flips over.
            val waitMs = 60_000L - (System.currentTimeMillis() % 60_000L)
            delay(waitMs.coerceAtLeast(1_000L))
            timeText = formatNow()
        }
    }
    HgPanel(
        cornerRadius = 12.dp,
        contentPadding = 10.dp,
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Pokeball(size = 18.dp)
            Spacer(Modifier.width(8.dp))
            Text(text = timeText, style = HgText.clock)
        }
    }
}

private fun formatNow(): String =
    LocalTime.now().format(DateTimeFormatter.ofPattern("HH:mm"))

@Composable
private fun PlayerCard(partyCount: Int, onOpenDrawer: () -> Unit) {
    HgPanel(modifier = Modifier.fillMaxWidth(), contentPadding = 10.dp) {
        Column {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .width(84.dp)
                        .height(50.dp)
                        .background(HgColors.Cream, RoundedCornerShape(6.dp)),
                ) {
                    MiniDiorama(modifier = Modifier.fillMaxSize())
                }
                Spacer(Modifier.width(10.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = stringResource(R.string.card_region),
                        style = HgText.micro.copy(color = HgColors.RedDeep),
                    )
                    Spacer(Modifier.height(2.dp))
                    Text(text = stringResource(R.string.card_party_label), style = HgText.body)
                    Spacer(Modifier.height(5.dp))
                    PartyIndicator(count = partyCount)
                }
            }
            Spacer(Modifier.height(9.dp))
            // Full width action: a pixel font button never has to fight for space.
            HgButton(
                text = stringResource(R.string.card_open_apps),
                onClick = onOpenDrawer,
                modifier = Modifier.fillMaxWidth(),
                minHeight = 40.dp,
            )
        }
    }
}

@Composable
private fun PartyGrid(
    state: LauncherUiState,
    settings: LauncherSettings,
    modifier: Modifier = Modifier,
    onLaunchSlot: (PartySlot) -> Unit,
    onSlotLongPress: (PartySlot) -> Unit,
    onAddFavourite: () -> Unit,
    iconProvider: (AppEntry) -> Drawable?,
) {
    val slots: List<PartySlot?> = remember(state.party) {
        val padded = state.party.toMutableList<PartySlot?>()
        while (padded.size < 6) padded.add(null)
        padded.take(6)
    }

    LazyVerticalGrid(
        columns = GridCells.Fixed(settings.columns),
        state = rememberLazyGridState(),
        modifier = modifier,
        contentPadding = PaddingValues(vertical = 4.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        itemsIndexed(slots) { index, slot ->
            val entry = slot?.let { state.installedAppsByKey[it.key] }
            PartySlotCard(
                slot = slot,
                icon = rememberAppIcon(entry, iconProvider),
                style = settings.cardStyle,
                slotIndex = index,
                onClick = {
                    if (slot == null) onAddFavourite() else onLaunchSlot(slot)
                },
                onLongClick = { slot?.let(onSlotLongPress) },
            )
        }

        if (state.party.isEmpty() && !state.loading) {
            item(span = { GridItemSpan(maxLineSpan) }) {
                HgPanel(modifier = Modifier.fillMaxWidth(), contentPadding = 14.dp) {
                    Column {
                        Text(
                            text = stringResource(R.string.status_empty_title),
                            style = HgText.heading,
                        )
                        Spacer(Modifier.height(8.dp))
                        Text(
                            text = stringResource(R.string.status_empty_body),
                            style = HgText.bodySoft,
                        )
                        Spacer(Modifier.height(12.dp))
                        HgButton(
                            text = stringResource(R.string.action_pick_apps),
                            onClick = onAddFavourite,
                        )
                    }
                }
            }
        }

        item(span = { GridItemSpan(maxLineSpan) }) {
            StatusCard(partyCount = state.party.size, loading = state.loading)
        }
    }
}

@Composable
private fun StatusCard(partyCount: Int, loading: Boolean) {
    HgPanel(modifier = Modifier.fillMaxWidth(), contentPadding = 12.dp) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Pokeball(size = 22.dp)
            Spacer(Modifier.width(10.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = if (loading) {
                        stringResource(R.string.status_loading)
                    } else {
                        stringResource(R.string.status_party_filled, partyCount)
                    },
                    style = HgText.small,
                )
                Spacer(Modifier.height(2.dp))
                Text(text = stringResource(R.string.status_hint), style = HgText.tiny)
            }
        }
    }
}
