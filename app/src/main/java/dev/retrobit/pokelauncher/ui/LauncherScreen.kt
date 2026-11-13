package dev.retrobit.pokelauncher.ui

import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import dev.retrobit.pokelauncher.data.AppEntry
import dev.retrobit.pokelauncher.ui.components.CloseIcon
import dev.retrobit.pokelauncher.ui.components.HgIconButton
import dev.retrobit.pokelauncher.ui.components.rememberAppIcon
import dev.retrobit.pokelauncher.ui.screens.AppDrawerScreen
import dev.retrobit.pokelauncher.ui.screens.AppInfoSheet
import dev.retrobit.pokelauncher.ui.screens.HgDialog
import dev.retrobit.pokelauncher.ui.screens.MenuSheet
import dev.retrobit.pokelauncher.ui.screens.SettingsContent
import dev.retrobit.pokelauncher.ui.screens.SettingsScreen
import dev.retrobit.pokelauncher.ui.theme.HgColors
import dev.retrobit.pokelauncher.ui.theme.HgText
import dev.retrobit.pokelauncher.R

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
    var showManualHomeDialog by rememberSaveable { mutableStateOf(false) }

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
            // Home content: a clean, empty screen. Everything else the
            // launcher offers lives in the drawer, menu and settings layers.
            Box(modifier = Modifier.weight(1f)) {
                HomeSurface()
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
                confirmLabel = stringResource(R.string.dialog_set_default_confirm),
                dismissLabel = stringResource(R.string.dialog_open_settings),
                onConfirm = {
                    showSetDefaultDialog = false
                    // Preferred path on Android 10+: the system shows its own
                    // "use PokeLauncher as home?" role dialog, no Settings trip.
                    if (!viewModel.requestHomeRole()) {
                        // EMUI / HarmonyOS hide the HOME picker behind their own
                        // app settings; when nothing resolves, the guide below
                        // spells the manual path out.
                        if (!viewModel.openHomeSettings()) showManualHomeDialog = true
                    }
                },
                onDismiss = {
                    // "Buka pengaturan" keeps the old explicit route available.
                    showSetDefaultDialog = false
                    if (!viewModel.openHomeSettings()) showManualHomeDialog = true
                },
            )
        }

        if (showManualHomeDialog) {
            HgDialog(
                title = stringResource(R.string.dialog_manual_home_title),
                body = stringResource(R.string.dialog_manual_home_body),
                confirmLabel = stringResource(R.string.dialog_ok),
                onConfirm = { showManualHomeDialog = false },
                onDismiss = { showManualHomeDialog = false },
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

@Composable
private fun HomeSurface() {
    // Clean home screen: nothing but the wallpaper colour. No clock, no party
    // cards, no status strip, no illustration - a blank canvas for the user's
    // own widgets. Launcher modes (drawer, settings, menu) still work through
    // Back/long press handlers in LauncherScreen.
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(HgColors.Paper),
    )
}
