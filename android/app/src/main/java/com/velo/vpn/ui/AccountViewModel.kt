package com.velo.vpn.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.velo.vpn.core.AppContainer
import com.velo.vpn.data.VeloApiException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch


data class AccountUiState(
    val loading: Boolean = true,
    val loggedIn: Boolean = false,
    val email: String = "",
    val hearts: Int = 0,
    val subscriptionActive: Boolean = false,
    val subscriptionEndsAt: String? = null,
    val otpSent: Boolean = false,
    val pendingEmail: String = "",
    val devCode: String? = null,
    val error: String? = null,
    val info: String? = null,
)

class AccountViewModel(private val container: AppContainer) : ViewModel() {
    private val repository = container.repository
    private val _state = MutableStateFlow(AccountUiState())
    val state: StateFlow<AccountUiState> = _state.asStateFlow()

    init { refresh() }

    fun refresh() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            if (!repository.isLoggedIn()) {
                _state.value = AccountUiState(loading = false)
                return@launch
            }
            try {
                val me = repository.me()
                val hearts = repository.hearts()
                val sub = repository.subscription()
                _state.value = _state.value.copy(
                    loading = false,
                    loggedIn = true,
                    email = me.email,
                    hearts = hearts.balance,
                    subscriptionActive = sub.active,
                    subscriptionEndsAt = sub.endsAt,
                    otpSent = false,
                    pendingEmail = "",
                    devCode = null,
                )
            } catch (t: Throwable) {
                _state.value = AccountUiState(loading = false, error = friendly(t))
            }
        }
    }

    fun requestOtp(email: String) {
        if (email.isBlank()) return
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null, info = null)
            try {
                val r = repository.requestOtp(email)
                if (!r.sent) throw VeloApiException(503, "email_unavailable")
                _state.value = _state.value.copy(
                    loading = false,
                    otpSent = true,
                    pendingEmail = email.trim(),
                    devCode = r.devCode,
                    info = "کد ورود به ایمیل شما ارسال شد.",
                )
            } catch (t: Throwable) {
                _state.value = _state.value.copy(loading = false, error = friendly(t))
            }
        }
    }

    fun verifyOtp(code: String, onSuccess: (() -> Unit)? = null) {
        val email = _state.value.pendingEmail
        if (email.isBlank() || code.length != 6) return
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            try {
                repository.verifyOtpAndLink(email, code)
                val me = repository.me()
                val hearts = repository.hearts()
                val sub = repository.subscription()
                _state.value = AccountUiState(
                    loading = false,
                    loggedIn = true,
                    email = me.email,
                    hearts = hearts.balance,
                    subscriptionActive = sub.active,
                    subscriptionEndsAt = sub.endsAt,
                    info = "حساب Velo شما فعال شد.",
                )
                onSuccess?.invoke()
            } catch (t: Throwable) {
                _state.value = _state.value.copy(loading = false, error = friendly(t))
            }
        }
    }

    fun logout(onDone: (() -> Unit)? = null) {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            repository.logout()
            _state.value = AccountUiState(loading = false, info = "از حساب خارج شدید.")
            onDone?.invoke()
        }
    }

    fun clearNotice() {
        _state.value = _state.value.copy(error = null, info = null)
    }

    private fun friendly(t: Throwable): String = when (t) {
        is VeloApiException -> when (t.apiDetail) {
            "invalid_code" -> "کد واردشده صحیح نیست یا منقضی شده است."
            "account_required" -> "برای این بخش ابتدا وارد حساب Velo شوید."
            "too_many_otp_requests" -> "درخواست کد زیادی ثبت شده؛ چند دقیقه دیگر دوباره امتحان کنید."
            "email_unavailable" -> "سرویس ایمیل Velo فعلاً در دسترس نیست."
            else -> "عملیات حساب انجام نشد. دوباره امتحان کنید."
        }
        else -> "ارتباط با Velo برقرار نشد. اینترنت خود را بررسی کنید."
    }

    class Factory(private val container: AppContainer) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T = AccountViewModel(container) as T
    }
}
