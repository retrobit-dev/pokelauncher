package dev.retrobit.pokelauncher.ui

import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
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
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
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
import androidx.lifecycle.viewmodel.compose.viewModel
import dev.retrobit.pokelauncher.game.GameMap
import dev.retrobit.pokelauncher.game.World
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
    val context = LocalContext.current
    val game: GameViewModel = viewModel(factory = GameViewModel.Factory(context))
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
                HomeSurface(
                    game = game,
                    onOpenLauncher = { showDrawer = true },
                    onOpenMenu = { showMenu = true },
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

/**
 * Whether the home screen draws the world.
 *
 * Off while the UI is rebuilt step by step: the screen is a clean paper canvas
 * and every element comes back deliberately. The world, its rules and the
 * renderer are untouched behind this flag, so switching it to `true` restores
 * the previous home screen in one line.
 */
private const val SHOW_WORLD = false

@Composable
private fun HomeSurface(
    game: GameViewModel,
    onOpenLauncher: () -> Unit,
    onOpenMenu: () -> Unit,
) {
    if (!SHOW_WORLD) {
        // The screen is the map, seen through the camera. No HUD, no field
        // decorations, no grid: this step is only about whether following the
        // player feels right on a real panel.
        val state by game.state.collectAsState()
        val world = state.world
        if (world == null || state.atlas == null) {
            Box(modifier = Modifier.fillMaxSize().background(HgColors.Paper))
            return
        }

        // Report the real panel, in map pixels. The rig works in map pixels, so
        // this is the only place that knows how much of the map fits.
        BoxWithConstraints(modifier = Modifier.fillMaxSize()) {
            val density = LocalDensity.current
            val viewPx = with(density) {
                ((maxWidth.toPx() / state.scale).toInt().coerceAtLeast(GameMap.TILE)) to
                    ((maxHeight.toPx() / state.scale).toInt().coerceAtLeast(GameMap.TILE))
            }
            LaunchedEffect(viewPx.first, viewPx.second, state.scale) {
                game.onViewportChanged(viewPx.first, viewPx.second, state.scale)
            }

            WorldCanvas(
                map = state.map,
                tiles = state.tiles,
                atlas = state.atlas,
                playerSheet = state.playerSheet,
                camera = state.camera,
                playerX = world.playerX,
                playerY = world.playerY,
                facing = world.facing,
                stepParity = state.stepParity,
                walking = state.walking,
                scale = state.scale,
                nightAmount = 0f,
                litAt = { _, _ -> false },
                builtAt = { x, y -> world.builtAt(x, y) != null },
                cropsAt = { x, y -> world.cropAt(x, y)?.stage(state.day) ?: 0 },
                onCellTap = game::tapCell,
                onZoom = game::zoomBy,
                modifier = Modifier.fillMaxSize(),
            )
        }
        return
    }

    val state by game.state.collectAsState()
    val world = state.world
    val atlas = state.atlas

    // Until the atlas and map load, show the paper screen rather than a flash of
    // half a world. It is also the fallback if the assets are missing.
    if (!state.ready || world == null || atlas == null) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(HgColors.Paper),
        )
        return
    }

    // Re-read the revision so a change made inside the world (a mined tree, a
    // planted seed) invalidates this scope even though World mutates in place.
    @Suppress("UNUSED_EXPRESSION")
    state.revision

    BoxWithConstraints(modifier = Modifier.fillMaxSize()) {
        val density = LocalDensity.current
        // The view size in pixels decides how much of the map fits and keeps the
        // camera clamped to the map edge.
        val viewPx = with(density) {
            (maxWidth.toPx().toInt() / state.scale).coerceAtLeast(GameMap.TILE) to
                (maxHeight.toPx().toInt() / state.scale).coerceAtLeast(GameMap.TILE)
        }
        val camera = remember(state.revision, viewPx, state.scale) {
            state.camera.copy(
                viewWidth = viewPx.first,
                viewHeight = viewPx.second,
                mapWidth = state.map.widthPx,
                mapHeight = state.map.heightPx,
            ).follow(world.playerX * GameMap.TILE, world.playerY * GameMap.TILE)
        }

        WorldCanvas(
            map = state.map,
            tiles = state.tiles,
            atlas = atlas,
            playerSheet = state.playerSheet,
            camera = camera,
            playerX = world.playerX,
            playerY = world.playerY,
            facing = world.facing,
            stepParity = state.stepParity,
            walking = state.walking,
            scale = state.scale,
            nightAmount = 1f - state.clock.daylight,
            litAt = { x, y -> world.isLit(x, y) },
            builtAt = { x, y -> world.builtAt(x, y) != null },
            cropsAt = { x, y -> world.cropAt(x, y)?.stage(state.day) ?: 0 },
            onCellTap = game::tapCell,
            onZoom = game::zoomBy,
            modifier = Modifier.fillMaxSize(),
        )

        GameHud(
            clock = state.clock,
            health = world.health,
            maxHealth = World.MAX_HEALTH,
            hunger = world.hunger,
            maxHunger = World.MAX_HUNGER,
            wood = world.wood,
            stone = world.stone,
            food = world.food,
            seeds = world.seeds,
            nearMachine = game.nearMachine(),
            message = state.message,
            messageId = state.messageId,
            onOpenLauncher = onOpenLauncher,
            onOpenMenu = onOpenMenu,
            onEat = game::eat,
            onTill = game::useUnderfoot,
            onPlaceLight = game::craftLight,
        )
    }
}
