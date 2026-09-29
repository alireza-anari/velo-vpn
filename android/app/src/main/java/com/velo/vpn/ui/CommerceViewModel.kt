package com.velo.vpn.ui

import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.velo.vpn.core.AppContainer
import com.velo.vpn.data.PublicConfig
import com.velo.vpn.data.VeloApiException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch


data class CommerceUiState(
    val loading: Boolean = true,
    val config: PublicConfig? = null,
    val submitting: Boolean = false,
    val pendingPaymentId: Long? = null,
    val error: String? = null,
    val info: String? = null,
)

class CommerceViewModel(private val container: AppContainer) : ViewModel() {
    private val repo = container.repository
    private val _state = MutableStateFlow(CommerceUiState())
    val state: StateFlow<CommerceUiState> = _state.asStateFlow()

    init { refreshConfig() }

    fun refreshConfig() = viewModelScope.launch {
        try {
            _state.value = _state.value.copy(loading = true, error = null)
            _state.value = _state.value.copy(loading = false, config = repo.config())
        } catch (_: Throwable) {
            _state.value = _state.value.copy(loading = false, error = "اطلاعات خرید فعلاً در دسترس نیست.")
        }
    }

    fun submit(
        context: Context,
        uri: Uri,
        kind: String,
        amountToman: Int,
        planCode: String?,
        requestedHearts: Int,
    ) = viewModelScope.launch {
        _state.value = _state.value.copy(submitting = true, error = null, info = null)
        try {
            val resolver = context.contentResolver
            val mime = resolver.getType(uri) ?: "image/jpeg"
            val bytes = resolver.openInputStream(uri)?.use { it.readBytes() }
                ?: throw IllegalStateException("receipt_unreadable")
            if (bytes.size > 8 * 1024 * 1024) throw IllegalArgumentException("receipt_too_large")
            var name = "receipt"
            resolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { cursor ->
                if (cursor.moveToFirst()) name = cursor.getString(0) ?: name
            }
            val result = repo.submitManualPayment(
                kind = kind,
                amountToman = amountToman,
                planCode = planCode,
                requestedHearts = requestedHearts,
                fileName = name,
                mimeType = mime,
                bytes = bytes,
            )
            _state.value = _state.value.copy(
                submitting = false,
                pendingPaymentId = result.id,
                info = "رسید ارسال شد و در انتظار بررسی است.",
            )
        } catch (t: Throwable) {
            _state.value = _state.value.copy(submitting = false, error = friendly(t))
        }
    }

    fun clearNotice() { _state.value = _state.value.copy(error = null, info = null) }

    private fun friendly(t: Throwable): String = when (t) {
        is VeloApiException -> when (t.apiDetail) {
            "account_required", "user_token_required" -> "برای پرداخت ابتدا با ایمیل وارد حساب Velo شوید."
            "premium_amount_mismatch" -> "قیمت پلن تغییر کرده است؛ صفحه را دوباره باز کنید."
            "insufficient_hearts" -> "تعداد قلب‌های شما برای این تخفیف کافی نیست."
            "invalid_receipt_type" -> "فقط تصویر یا PDF رسید قابل قبول است."
            "receipt_too_large" -> "حجم رسید باید کمتر از ۸ مگابایت باشد."
            else -> "ارسال پرداخت انجام نشد. دوباره امتحان کنید."
        }
        is IllegalArgumentException -> "حجم یا فایل رسید معتبر نیست."
        else -> "ارسال رسید انجام نشد. اینترنت خود را بررسی کنید."
    }

    class Factory(private val container: AppContainer) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T = CommerceViewModel(container) as T
    }
}
