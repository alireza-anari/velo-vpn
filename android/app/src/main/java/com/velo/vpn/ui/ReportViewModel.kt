package com.velo.vpn.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.velo.vpn.core.AppContainer
import com.velo.vpn.data.ReportSummary
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch


data class ReportUiState(val loading: Boolean = true, val report: ReportSummary? = null, val error: String? = null)

class ReportViewModel(private val container: AppContainer) : ViewModel() {
    private val _state = MutableStateFlow(ReportUiState())
    val state: StateFlow<ReportUiState> = _state.asStateFlow()
    init { refresh() }

    fun refresh() = viewModelScope.launch {
        _state.value = _state.value.copy(loading = true, error = null)
        try {
            _state.value = ReportUiState(loading = false, report = container.repository.report())
        } catch (_: Throwable) {
            _state.value = ReportUiState(loading = false, error = "گزارش فعلاً در دسترس نیست.")
        }
    }

    class Factory(private val container: AppContainer) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T = ReportViewModel(container) as T
    }
}
