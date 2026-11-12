package dev.retrobit.pokelauncher.ui

import android.graphics.drawable.Drawable
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import dev.retrobit.pokelauncher.data.AppEntry
import dev.retrobit.pokelauncher.data.CardStyle
import dev.retrobit.pokelauncher.data.LauncherRepository
import dev.retrobit.pokelauncher.data.LauncherUiState
import dev.retrobit.pokelauncher.data.PartyRules
import dev.retrobit.pokelauncher.data.PartySlot
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * Single source of truth for the launcher. Platform work runs on Dispatchers.IO
 * because querying PackageManager and inflating icons can take a while on cold
 * start, and a home screen must never block its first frame.
 */
class LauncherViewModel(private val repository: LauncherRepository) : ViewModel() {

    private val _state = MutableStateFlow(LauncherUiState())
    val state: StateFlow<LauncherUiState> = _state.asStateFlow()

    private var partyKeys: List<String> = repository.loadParty()

    init {
        refresh()
    }

    /** Re-queries installed apps; call on ON_RESUME so installs show up immediately. */
    fun refresh() {
        viewModelScope.launch {
            val (apps, settings) = withContext(Dispatchers.IO) {
                repository.loadApps() to repository.loadSettings()
            }
            _state.update { current ->
                current.copy(
                    apps = apps,
                    party = buildParty(apps),
                    settings = settings,
                    loading = false,
                )
            }
        }
    }

    fun iconFor(entry: AppEntry): Drawable? = repository.iconFor(entry)

    fun launch(entry: AppEntry): Boolean {
        val ok = repository.startApp(entry)
        if (ok) {
            repository.recordLaunch(entry.key)
            _state.update { current -> current.copy(party = buildParty(current.apps)) }
        }
        return ok
    }

    fun openAppInfo(packageName: String) = repository.openAppInfo(packageName)

    fun uninstall(packageName: String) = repository.uninstall(packageName)

    fun openHomeSettings() = repository.openHomeSettings()

    // ------------------------------------------------------------- party

    /** Returns true when the party changed, false when it was already full. */
    fun toggleParty(key: String): Boolean {
        val next = PartyRules.toggle(partyKeys, key)
        if (next == partyKeys) return false
        partyKeys = next
        repository.saveParty(next)
        _state.update { current -> current.copy(party = buildParty(current.apps)) }
        return true
    }

    fun removeFromParty(key: String) {
        if (key !in partyKeys) return
        partyKeys = PartyRules.remove(partyKeys, key)
        repository.saveParty(partyKeys)
        _state.update { current -> current.copy(party = buildParty(current.apps)) }
    }

    fun isPartyFull(): Boolean = PartyRules.isFull(partyKeys)

    private fun buildParty(apps: List<AppEntry>): List<PartySlot> {
        val byKey = apps.associateBy { it.key }
        return partyKeys.map { key ->
            val installed = byKey[key]
            val packageName = key.substringBefore('/')
            val activityName = key.substringAfter('/', missingDelimiterValue = "")
            PartySlot(
                key = key,
                packageName = packageName,
                activityName = activityName,
                label = installed?.label ?: packageName.substringAfterLast('.'),
                installed = installed != null,
                level = PartyRules.levelFor(repository.loadLaunchCount(key)),
            )
        }
    }

    // ---------------------------------------------------------- settings

    fun setColumns(columns: Int) {
        repository.saveColumns(columns)
        _state.update { it.copy(settings = it.settings.copy(columns = columns)) }
    }

    fun setShowClock(show: Boolean) {
        repository.saveShowClock(show)
        _state.update { it.copy(settings = it.settings.copy(showClock = show)) }
    }

    fun setCardStyle(style: CardStyle) {
        repository.saveCardStyle(style)
        _state.update { it.copy(settings = it.settings.copy(cardStyle = style)) }
    }

    companion object {
        fun factory(repository: LauncherRepository): ViewModelProvider.Factory = viewModelFactory {
            initializer { LauncherViewModel(repository) }
        }
    }
}
