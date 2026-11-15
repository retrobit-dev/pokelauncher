package dev.retrobit.pokelauncher

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import dev.retrobit.pokelauncher.data.LauncherRepository
import dev.retrobit.pokelauncher.ui.LauncherScreen
import dev.retrobit.pokelauncher.ui.LauncherViewModel
import dev.retrobit.pokelauncher.ui.theme.PokeLauncherTheme

/**
 * The home screen. A single activity, no fragments: every surface (party grid,
 * drawer, settings, sheets) is a Compose layer.
 */
class MainActivity : ComponentActivity() {

    private val viewModel: LauncherViewModel by viewModels {
        LauncherViewModel.factory(LauncherRepository(applicationContext))
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            PokeLauncherTheme {
                LauncherScreen(viewModel = viewModel)
            }
        }
    }

    /**
     * Coming back from an installed/uninstalled app should be instant, so the
     * list is refreshed every time the launcher is resumed.
     */
    override fun onResume() {
        super.onResume()
        viewModel.refresh()
    }
}
