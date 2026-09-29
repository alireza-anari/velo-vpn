package com.velo.vpn.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.velo.vpn.core.AppContainer
import com.velo.vpn.data.MissionTodayResponse
import com.velo.vpn.data.OneTimeMissionsResponse
import com.velo.vpn.data.ReferralSummary
import com.velo.vpn.data.WeeklyMissionsResponse
import com.velo.vpn.data.VeloApiException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch


data class RewardsUiState(
    val loadingMissions: Boolean = false,
    val missions: MissionTodayResponse? = null,
    val loadingWeekly: Boolean = false,
    val weekly: WeeklyMissionsResponse? = null,
    val loadingReferrals: Boolean = false,
    val referrals: ReferralSummary? = null,
    val loadingOneTime: Boolean = false,
    val oneTime: OneTimeMissionsResponse? = null,
    val error: String? = null,
    val info: String? = null,
)

class RewardsViewModel(private val container: AppContainer) : ViewModel() {
    private val repository = container.repository
    private val _state = MutableStateFlow(RewardsUiState())
    val state: StateFlow<RewardsUiState> = _state.asStateFlow()

    fun refreshMissions() = viewModelScope.launch {
        _state.value = _state.value.copy(loadingMissions = true, error = null)
        try {
            _state.value = _state.value.copy(loadingMissions = false, missions = repository.missionsToday())
        } catch (t: Throwable) {
            _state.value = _state.value.copy(loadingMissions = false, error = friendly(t))
        }
    }

    fun claimMission(key: String) = viewModelScope.launch {
        try {
            val result = repository.claimMission(key)
            _state.value = _state.value.copy(info = "+${result.hearts} قلب دریافت شد")
            refreshMissions()
        } catch (t: Throwable) {
            _state.value = _state.value.copy(error = friendly(t))
        }
    }


    fun refreshWeekly() = viewModelScope.launch {
        _state.value = _state.value.copy(loadingWeekly = true, error = null)
        try {
            _state.value = _state.value.copy(loadingWeekly = false, weekly = repository.missionsWeekly())
        } catch (t: Throwable) {
            _state.value = _state.value.copy(loadingWeekly = false, error = friendly(t))
        }
    }

    fun claimWeekly(key: String) = viewModelScope.launch {
        try {
            val result = repository.claimWeeklyMission(key)
            _state.value = _state.value.copy(info = "+${result.hearts} قلب دریافت شد")
            refreshWeekly()
        } catch (t: Throwable) {
            _state.value = _state.value.copy(error = friendly(t))
        }
    }

    fun refreshOneTime() = viewModelScope.launch {
        _state.value = _state.value.copy(loadingOneTime = true, error = null)
        try {
            _state.value = _state.value.copy(loadingOneTime = false, oneTime = repository.oneTimeMissions())
        } catch (t: Throwable) {
            _state.value = _state.value.copy(loadingOneTime = false, error = friendly(t))
        }
    }

    fun openOneTime(key: String, onUrl: (String) -> Unit) = viewModelScope.launch {
        try {
            val result = repository.openOneTimeMission(key)
            onUrl(result.url)
            refreshOneTime()
        } catch (t: Throwable) {
            _state.value = _state.value.copy(error = friendly(t))
        }
    }

    fun claimOneTime(key: String) = viewModelScope.launch {
        try {
            val result = repository.claimOneTimeMission(key)
            _state.value = _state.value.copy(info = "+${result.hearts} قلب دریافت شد")
            refreshOneTime()
        } catch (t: Throwable) {
            _state.value = _state.value.copy(error = friendly(t))
        }
    }

    fun refreshReferrals() = viewModelScope.launch {
        _state.value = _state.value.copy(loadingReferrals = true, error = null)
        try {
            _state.value = _state.value.copy(loadingReferrals = false, referrals = repository.referrals())
        } catch (t: Throwable) {
            _state.value = _state.value.copy(loadingReferrals = false, error = friendly(t))
        }
    }

    fun clearNotice() { _state.value = _state.value.copy(error = null, info = null) }

    private fun friendly(t: Throwable): String = when (t) {
        is VeloApiException -> when (t.apiDetail) {
            "account_required", "user_token_required" -> "برای دریافت قلب و دعوت دوستان ابتدا با ایمیل وارد حساب Velo شوید."
            "mission_not_complete" -> "این ماموریت هنوز کامل نشده است."
            "already_claimed" -> "پاداش این ماموریت قبلاً دریافت شده است."
            "wait_before_claim" -> "چند ثانیه بعد از بازکردن صفحه دوباره دریافت پاداش را بزنید."
            "mission_not_available" -> "این ماموریت هنوز فعال نشده است."
            else -> "این بخش فعلاً در دسترس نیست. دوباره امتحان کنید."
        }
        else -> "ارتباط با Velo برقرار نشد."
    }

    class Factory(private val container: AppContainer) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T = RewardsViewModel(container) as T
    }
}
