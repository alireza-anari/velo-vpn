package com.velo.vpn.ui

import android.app.Activity
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.velo.vpn.BuildConfig
import com.velo.vpn.ads.TapsellRewardedAdManager
import com.velo.vpn.core.AppContainer
import com.velo.vpn.data.PublicConfig
import com.velo.vpn.data.ServerDto
import com.velo.vpn.data.VeloApiException
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch


data class HomeUiState(
    val ready: Boolean = false,
    val busy: Boolean = false,
    val adBusy: Boolean = false,
    val connected: Boolean = false,
    val premium: Boolean = false,
    val freeSpeedMbps: Int = 2,
    val adRewardMinutes: Int = 20,
    val remainingSeconds: Int = 0,
    val serverName: String = "بهترین سرور",
    val serverCountryCode: String = "",
    val selectedServerId: Long? = null,
    val servers: List<ServerDto> = emptyList(),
    val sessionId: Long? = null,
    val error: String? = null,
    val info: String? = null,
    val takeoverRequired: Boolean = false,
)

class VeloViewModel(private val container: AppContainer) : ViewModel() {
    private val repository = container.repository
    private val tunnel = container.tunnelManager
    private val ads = container.rewardedAds

    private val _home = MutableStateFlow(HomeUiState())
    val home: StateFlow<HomeUiState> = _home.asStateFlow()

    private var config: PublicConfig? = null
    private var heartbeatJob: Job? = null
    private var timerJob: Job? = null

    init {
        viewModelScope.launch { bootstrap() }
    }

    private suspend fun bootstrap() {
        _home.value = _home.value.copy(busy = true, error = null)
        try {
            val referralCode = runCatching { container.referralAttribution.readReferralCode() }.getOrNull()
            repository.ensureDevice(referralCode)
            config = repository.config()
            val free = repository.freeStatus()
            val remote = repository.vpnStatus()
            val localConnected = tunnel.isConnected()

            var sessionId: Long? = remote.sessionId
            var connected = remote.connected && localConnected
            if (remote.connected && !localConnected && remote.sessionId != null) {
                runCatching { repository.disconnect(remote.sessionId) }
                sessionId = null
                connected = false
            } else if (!remote.connected && localConnected) {
                runCatching { tunnel.disconnect() }
                connected = false
            }

            _home.value = _home.value.copy(
                ready = true,
                busy = false,
                connected = connected,
                premium = remote.premium,
                freeSpeedMbps = remote.effectiveFreeSpeedMbps ?: config?.freeSpeedMbps ?: 2,
                adRewardMinutes = config?.adRewardMinutes ?: 20,
                remainingSeconds = if (remote.premium) 0 else free.remainingSeconds,
                sessionId = sessionId,
            )
            if (connected && sessionId != null) {
                if (remote.reconnectRequired) {
                    scheduleAutoReconnect(sessionId)
                } else {
                    startConnectionJobs(sessionId, remote.premium)
                }
            }
        } catch (t: Throwable) {
            _home.value = _home.value.copy(ready = true, busy = false, error = friendly(t))
        }
    }

    fun connect(forceTakeover: Boolean = false, serverId: Long? = null) {
        if (_home.value.busy || _home.value.connected) return
        viewModelScope.launch {
            _home.value = _home.value.copy(busy = true, error = null, info = null, takeoverRequired = false)
            var remoteSessionId: Long? = null
            try {
                val publicKey = tunnel.prepareClientPublicKey()
                val requestedServerId = serverId ?: _home.value.selectedServerId
                val remote = repository.connect(publicKey, requestedServerId, forceTakeover)
                remoteSessionId = remote.sessionId
                tunnel.connect(remote)
                _home.value = _home.value.copy(
                    busy = false,
                    connected = true,
                    premium = remote.premium,
                    sessionId = remote.sessionId,
                    serverName = remote.serverName,
                    serverCountryCode = remote.countryCode,
                    remainingSeconds = remote.freeRemainingSecondsBeforeStart ?: _home.value.remainingSeconds,
                )
                startConnectionJobs(remote.sessionId, remote.premium)
            } catch (t: Throwable) {
                if (remoteSessionId != null) runCatching { repository.disconnect(remoteSessionId) }
                val takeover = t is VeloApiException && t.apiDetail == "premium_active_on_other_device"
                _home.value = _home.value.copy(
                    busy = false,
                    error = if (takeover) "اشتراک شما روی دستگاه دیگری در حال استفاده است." else friendly(t),
                    takeoverRequired = takeover,
                )
            }
        }
    }

    fun disconnect() {
        val sessionId = _home.value.sessionId
        if (_home.value.busy || !_home.value.connected) return
        viewModelScope.launch {
            _home.value = _home.value.copy(busy = true, error = null)
            heartbeatJob?.cancel(); timerJob?.cancel()
            runCatching { tunnel.disconnect() }
            if (sessionId != null) runCatching { repository.disconnect(sessionId) }
            try {
                val free = repository.freeStatus()
                val remote = repository.vpnStatus()
                _home.value = _home.value.copy(
                    busy = false,
                    connected = false,
                    premium = remote.premium,
                    sessionId = null,
                    remainingSeconds = if (remote.premium) 0 else free.remainingSeconds,
                    freeSpeedMbps = remote.effectiveFreeSpeedMbps ?: _home.value.freeSpeedMbps,
                )
            } catch (t: Throwable) {
                _home.value = _home.value.copy(busy = false, connected = false, sessionId = null, error = friendly(t))
            }
        }
    }


    fun refreshServers() {
        viewModelScope.launch {
            try {
                val remote = repository.vpnStatus()
                val servers = if (remote.premium) repository.servers() else emptyList()
                _home.value = _home.value.copy(
                    premium = remote.premium,
                    servers = servers,
                    freeSpeedMbps = remote.effectiveFreeSpeedMbps ?: _home.value.freeSpeedMbps,
                )
            } catch (t: Throwable) {
                _home.value = _home.value.copy(error = friendly(t))
            }
        }
    }

    fun selectServer(server: ServerDto?) {
        if (server?.locked == true) {
            _home.value = _home.value.copy(info = "این سرور VIP است. از فروشگاه قلب‌ها می‌توانید آن را فعال کنید.")
            return
        }
        if (server?.available == false) {
            _home.value = _home.value.copy(info = "این سرور موقتاً در دسترس نیست. بهترین سرور را انتخاب کنید.")
            return
        }
        _home.value = _home.value.copy(
            selectedServerId = server?.id,
            serverName = server?.let { if (it.city.isBlank()) it.name else "${it.name} • ${it.city}" } ?: "بهترین سرور",
            serverCountryCode = server?.countryCode ?: "",
        )
    }

    fun watchRewardedAd(activity: Activity) {
        if (_home.value.adBusy) return
        viewModelScope.launch {
            _home.value = _home.value.copy(adBusy = true, error = null, info = null)
            try {
                val cfg = config ?: repository.config().also { config = it }
                if (cfg.tapsellRewardedZoneId.isBlank() && BuildConfig.DEBUG) {
                    // Debug-only end-to-end path: exercises the real backend reward wallet
                    // without depending on live ad inventory during VPS/app integration tests.
                    val challenge = repository.createAdChallenge()
                    val result = repository.completeAd(challenge.nonce, "velo-debug-reward")
                    _home.value = _home.value.copy(
                        adBusy = false,
                        remainingSeconds = result.remainingSeconds,
                        info = "حالت تست: +${result.grantedSeconds / 60} دقیقه اضافه شد",
                    )
                    return@launch
                }
                if (cfg.tapsellRewardedZoneId.isBlank()) {
                    _home.value = _home.value.copy(adBusy = false, error = "تبلیغات تپسل هنوز در پنل Velo تنظیم نشده است.")
                    return@launch
                }
                val challenge = repository.createAdChallenge()
                ads.show(activity, cfg.tapsellRewardedZoneId, object : TapsellRewardedAdManager.Callback {
                    override fun onRewarded(responseId: String) {
                        viewModelScope.launch {
                            try {
                                val result = repository.completeAd(challenge.nonce, responseId)
                                _home.value = _home.value.copy(
                                    adBusy = false,
                                    remainingSeconds = result.remainingSeconds,
                                    info = "+${result.grantedSeconds / 60} دقیقه به زمان امروز اضافه شد",
                                )
                            } catch (t: Throwable) {
                                _home.value = _home.value.copy(adBusy = false, error = friendly(t))
                            }
                        }
                    }

                    override fun onError(message: String) {
                        _home.value = _home.value.copy(adBusy = false, error = friendlyCode(message))
                    }
                })
            } catch (t: Throwable) {
                _home.value = _home.value.copy(adBusy = false, error = friendly(t))
            }
        }
    }

    fun clearNotice() {
        _home.value = _home.value.copy(error = null, info = null, takeoverRequired = false)
    }

    private fun startConnectionJobs(sessionId: Long, premium: Boolean) {
        heartbeatJob?.cancel()
        heartbeatJob = viewModelScope.launch {
            var failures = 0
            while (true) {
                delay(30_000)
                try {
                    val heartbeat = repository.heartbeat(sessionId)
                    failures = 0
                    if (heartbeat.reconnectRequired) {
                        scheduleAutoReconnect(sessionId)
                        break
                    }
                } catch (t: Throwable) {
                    failures++
                    if (t is VeloApiException && t.apiDetail == "session_not_found") {
                        scheduleAutoReconnect(sessionId)
                        break
                    }
                    if (failures >= 3) {
                        runCatching { tunnel.disconnect() }
                        _home.value = _home.value.copy(
                            connected = false,
                            sessionId = null,
                            error = "ارتباط با سرویس Velo قطع شد. اینترنت خود را بررسی کنید.",
                        )
                        break
                    }
                }
            }
        }

        timerJob?.cancel()
        if (!premium) {
            timerJob = viewModelScope.launch {
                while (_home.value.connected && !_home.value.premium) {
                    delay(1_000)
                    val next = (_home.value.remainingSeconds - 1).coerceAtLeast(0)
                    _home.value = _home.value.copy(remainingSeconds = next)
                    if (next == 0) {
                        disconnect()
                        break
                    }
                }
            }
        }
    }

    private fun scheduleAutoReconnect(oldSessionId: Long) {
        viewModelScope.launch {
            if (_home.value.sessionId != oldSessionId || !_home.value.connected) return@launch
            timerJob?.cancel()
            _home.value = _home.value.copy(busy = true, info = "در حال انتقال به یک سرور سالم…", error = null)
            runCatching { tunnel.disconnect() }
            runCatching { repository.disconnect(oldSessionId) }
            try {
                val publicKey = tunnel.prepareClientPublicKey()
                // Failover intentionally uses automatic selection even if the old server was manually selected.
                val remote = repository.connect(publicKey, null, false)
                tunnel.connect(remote)
                _home.value = _home.value.copy(
                    busy = false,
                    connected = true,
                    premium = remote.premium,
                    sessionId = remote.sessionId,
                    serverName = remote.serverName,
                    serverCountryCode = remote.countryCode,
                    selectedServerId = null,
                    remainingSeconds = remote.freeRemainingSecondsBeforeStart ?: _home.value.remainingSeconds,
                    info = "اتصال به سرور سالم منتقل شد",
                    error = null,
                )
                startConnectionJobs(remote.sessionId, remote.premium)
            } catch (t: Throwable) {
                runCatching { tunnel.disconnect() }
                _home.value = _home.value.copy(
                    busy = false,
                    connected = false,
                    sessionId = null,
                    error = friendly(t),
                )
            }
        }
    }

    private fun friendly(t: Throwable): String = when (t) {
        is VeloApiException -> friendlyCode(t.apiDetail)
        else -> "اتصال به سرویس Velo ممکن نشد. اینترنت خود را بررسی کنید."
    }

    private fun friendlyCode(code: String): String = when (code) {
        "no_free_time" -> "برای اتصال رایگان ابتدا یک ویدیو ببینید و زمان بگیرید."
        "no_server_capacity", "all_servers_unavailable", "server_temporarily_unhealthy" -> "سرورها فعلاً در دسترس نیستند. چند لحظه دیگر دوباره امتحان کنید."
        "no_accessible_server" -> "در حال حاضر سرور قابل استفاده‌ای برای حساب شما وجود ندارد."
        "premium_required" -> "این سرور مخصوص کاربران پریمیوم است."
        "vip_entitlement_required" -> "این سرور VIP است. از فروشگاه قلب‌ها فعالش کنید."
        "ad_closed_without_reward" -> "ویدیو کامل نشد و زمانی اضافه نشد."
        "too_many_ad_requests" -> "درخواست‌های زیادی ثبت شده؛ چند دقیقه دیگر دوباره امتحان کنید."
        else -> if (code.length < 90 && !code.contains("Exception")) code else "عملیات انجام نشد. دوباره امتحان کنید."
    }

    class Factory(private val container: AppContainer) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            return VeloViewModel(container) as T
        }
    }
}
