package com.velo.vpn.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.velo.vpn.core.AppContainer
import com.velo.vpn.data.StoreCatalogResponse
import com.velo.vpn.data.VeloApiException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class StoreUiState(
    val loading: Boolean = true,
    val catalog: StoreCatalogResponse? = null,
    val buyingSku: String? = null,
    val error: String? = null,
    val info: String? = null,
)

class StoreViewModel(private val container: AppContainer) : ViewModel() {
    private val repo = container.repository
    private val _state = MutableStateFlow(StoreUiState())
    val state: StateFlow<StoreUiState> = _state.asStateFlow()

    fun refresh() = viewModelScope.launch {
        _state.value = _state.value.copy(loading = true, error = null)
        try {
            _state.value = _state.value.copy(loading = false, catalog = repo.storeCatalog())
        } catch (t: Throwable) {
            _state.value = _state.value.copy(loading = false, error = friendly(t))
        }
    }

    fun buy(sku: String, onPurchased: (() -> Unit)? = null) = viewModelScope.launch {
        _state.value = _state.value.copy(buyingSku = sku, error = null, info = null)
        try {
            val result = repo.purchaseStoreItem(sku)
            _state.value = _state.value.copy(
                buyingSku = null,
                info = "خرید انجام شد. موجودی شما ${result.heartBalance} قلب است.",
            )
            refresh()
            onPurchased?.invoke()
        } catch (t: Throwable) {
            _state.value = _state.value.copy(buyingSku = null, error = friendly(t))
        }
    }

    fun clearNotice() { _state.value = _state.value.copy(error = null, info = null) }

    private fun friendly(t: Throwable): String = when (t) {
        is VeloApiException -> when (t.apiDetail) {
            "account_required", "user_token_required" -> "برای استفاده از فروشگاه ابتدا با ایمیل وارد حساب Velo شوید."
            "insufficient_hearts" -> "قلب کافی برای این خرید ندارید."
            "already_owned" -> "این آیتم قبلاً برای حساب شما فعال شده است."
            "store_item_not_ready" -> "این قابلیت هنوز آماده فعال‌سازی نیست."
            "store_item_unavailable" -> "این آیتم فعلاً در دسترس نیست."
            else -> "خرید انجام نشد. دوباره امتحان کنید."
        }
        else -> "ارتباط با فروشگاه Velo برقرار نشد."
    }

    class Factory(private val container: AppContainer) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T = StoreViewModel(container) as T
    }
}
