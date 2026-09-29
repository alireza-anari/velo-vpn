package com.velo.vpn.data

import com.google.gson.annotations.SerializedName

data class GuestRequest(
    @SerializedName("install_id") val installId: String,
    @SerializedName("referral_code") val referralCode: String? = null,
)

data class GuestResponse(
    @SerializedName("device_id") val deviceId: Long,
    @SerializedName("device_token") val deviceToken: String,
)

data class PublicConfig(
    @SerializedName("free_speed_mbps") val freeSpeedMbps: Int,
    @SerializedName("ad_reward_minutes") val adRewardMinutes: Int,
    @SerializedName("premium_prices") val premiumPrices: Map<String, Int>,
    @SerializedName("max_heart_discount_percent") val maxHeartDiscountPercent: Int,
    @SerializedName("heart_discount_tiers") val heartDiscountTiers: Map<String, Int>,
    @SerializedName("support_heart_tiers") val supportHeartTiers: Map<String, Int>,
    @SerializedName("manual_card_number") val manualCardNumber: String,
    @SerializedName("manual_card_holder") val manualCardHolder: String,
    @SerializedName("tapsell_app_key") val tapsellAppKey: String,
    @SerializedName("tapsell_rewarded_zone_id") val tapsellRewardedZoneId: String,
    @SerializedName("timezone_name") val timezoneName: String,
)

data class FreeStatus(
    @SerializedName("remaining_seconds") val remainingSeconds: Int,
    @SerializedName("earned_seconds") val earnedSeconds: Int,
    @SerializedName("consumed_seconds") val consumedSeconds: Int,
    @SerializedName("completed_ads") val completedAds: Int,
    @SerializedName("reset_at") val resetAt: String,
)

data class AdChallengeResponse(
    val nonce: String,
    @SerializedName("expires_in_seconds") val expiresInSeconds: Int,
)

data class AdCompleteRequest(
    val nonce: String,
    @SerializedName("client_event_id") val clientEventId: String,
    @SerializedName("provider_response_id") val providerResponseId: String?,
)

data class AdCompleteResponse(
    @SerializedName("granted_seconds") val grantedSeconds: Int,
    @SerializedName("remaining_seconds") val remainingSeconds: Int,
    @SerializedName("completed_ads") val completedAds: Int,
)

data class VpnConnectRequest(
    @SerializedName("client_public_key") val clientPublicKey: String,
    @SerializedName("server_id") val serverId: Long? = null,
    @SerializedName("force_takeover") val forceTakeover: Boolean = false,
)

data class VpnConnectResponse(
    @SerializedName("session_id") val sessionId: Long,
    val premium: Boolean,
    @SerializedName("client_address") val clientAddress: String,
    @SerializedName("server_public_key") val serverPublicKey: String,
    val endpoint: String,
    val dns: String,
    @SerializedName("allowed_ips") val allowedIps: List<String>,
    @SerializedName("persistent_keepalive") val persistentKeepalive: Int,
    @SerializedName("expires_at") val expiresAt: String?,
    @SerializedName("free_remaining_seconds_before_start") val freeRemainingSecondsBeforeStart: Int?,
    @SerializedName("server_id") val serverId: Long,
    @SerializedName("server_name") val serverName: String,
    @SerializedName("country_code") val countryCode: String,
)

data class VpnStatusResponse(
    val connected: Boolean,
    @SerializedName("session_id") val sessionId: Long?,
    val premium: Boolean,
    @SerializedName("expires_at") val expiresAt: String?,
    @SerializedName("free_remaining_seconds") val freeRemainingSeconds: Int?,
    @SerializedName("effective_free_speed_mbps") val effectiveFreeSpeedMbps: Int?,
    @SerializedName("reconnect_required") val reconnectRequired: Boolean = false,
)

data class VpnHeartbeatResponse(
    val ok: Boolean,
    @SerializedName("expires_at") val expiresAt: String?,
    val premium: Boolean,
    @SerializedName("free_remaining_seconds") val freeRemainingSeconds: Int?,
    @SerializedName("reconnect_required") val reconnectRequired: Boolean = false,
    @SerializedName("server_id") val serverId: Long,
)

data class ServerDto(
    val id: Long,
    val name: String,
    @SerializedName("country_code") val countryCode: String,
    val city: String,
    val tier: String,
    val locked: Boolean,
    val available: Boolean = true,
)

data class ApiError(val detail: String? = null)

data class OtpRequestBody(val email: String)
data class OtpRequestResponse(val sent: Boolean, @SerializedName("dev_code") val devCode: String? = null)
data class OtpVerifyBody(val email: String, val code: String)
data class AuthResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("user_id") val userId: Long,
    val email: String,
    @SerializedName("referral_code") val referralCode: String?,
)
data class LinkDeviceBody(@SerializedName("device_token") val deviceToken: String)
data class MeResponse(val id: Long, val email: String, @SerializedName("referral_code") val referralCode: String?)
data class HeartsResponse(val balance: Int)
data class SubscriptionResponse(val active: Boolean, @SerializedName("ends_at") val endsAt: String?, val source: String?)

data class ReportDay(val date: String, val seconds: Int, val bytes: Long)
data class ReportSummary(
    @SerializedName("today_seconds") val todaySeconds: Int,
    @SerializedName("today_rx_bytes") val todayRxBytes: Long,
    @SerializedName("today_tx_bytes") val todayTxBytes: Long,
    @SerializedName("today_connections") val todayConnections: Int,
    @SerializedName("today_ads") val todayAds: Int,
    @SerializedName("month_seconds") val monthSeconds: Int,
    @SerializedName("month_bytes") val monthBytes: Long,
    @SerializedName("last_7_days") val last7Days: List<ReportDay>,
)

data class MissionItemDto(
    val key: String,
    val title: String,
    val progress: Int,
    val target: Int,
    val hearts: Int,
    val complete: Boolean,
    val claimed: Boolean,
)
data class MissionTodayResponse(
    val date: String,
    @SerializedName("account_required_for_hearts") val accountRequiredForHearts: Boolean,
    val missions: List<MissionItemDto>,
    @SerializedName("daily_complete") val dailyComplete: Boolean,
    @SerializedName("daily_bonus_hearts") val dailyBonusHearts: Int,
    @SerializedName("daily_bonus_claimed") val dailyBonusClaimed: Boolean,
)
data class MissionClaimResponse(val claimed: Boolean, @SerializedName("mission_key") val missionKey: String, val hearts: Int)

data class ReferralItemDto(
    val id: Long,
    val label: String,
    val installed: Boolean,
    @SerializedName("rewarded_days") val rewardedDays: Int,
    val days: List<String>,
    val complete: Boolean,
)
data class ReferralSummary(
    val code: String,
    @SerializedName("share_url") val shareUrl: String,
    @SerializedName("install_reward_hearts") val installRewardHearts: Int,
    @SerializedName("daily_reward_hearts") val dailyRewardHearts: Int,
    val items: List<ReferralItemDto>,
)

data class PaymentCreated(val id: Long, val status: String)
data class PaymentItem(
    val id: Long,
    val kind: String,
    @SerializedName("amount_toman") val amountToman: Int,
    @SerializedName("plan_code") val planCode: String?,
    @SerializedName("requested_hearts") val requestedHearts: Int?,
    val status: String,
    @SerializedName("admin_note") val adminNote: String?,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("reviewed_at") val reviewedAt: String?,
)

data class OneTimeMissionDto(
    val key: String,
    val title: String,
    val url: String,
    val hearts: Int,
    val enabled: Boolean,
    val opened: Boolean,
    val claimed: Boolean,
)
data class OneTimeMissionsResponse(
    @SerializedName("account_required_for_hearts") val accountRequiredForHearts: Boolean,
    val missions: List<OneTimeMissionDto>,
    @SerializedName("verification_note") val verificationNote: String,
)
data class MissionOpenResponse(val opened: Boolean, val url: String)

data class WeeklyMissionsResponse(
    val period: String,
    @SerializedName("start_date") val startDate: String,
    @SerializedName("end_date") val endDate: String,
    @SerializedName("account_required_for_hearts") val accountRequiredForHearts: Boolean,
    val missions: List<MissionItemDto>,
    @SerializedName("weekly_complete") val weeklyComplete: Boolean,
    @SerializedName("weekly_bonus_hearts") val weeklyBonusHearts: Int,
    @SerializedName("weekly_bonus_claimed") val weeklyBonusClaimed: Boolean,
)

data class StoreItemDto(
    val sku: String,
    val title: String,
    val description: String,
    val kind: String,
    val target: String?,
    val value: Int?,
    val hearts: Int,
    @SerializedName("duration_days") val durationDays: Int,
    val enabled: Boolean,
    val badge: String,
    val owned: Boolean,
    val affordable: Boolean,
)

data class StoreCatalogResponse(
    @SerializedName("heart_balance") val heartBalance: Int,
    val items: List<StoreItemDto>,
)

data class StorePurchaseResponse(
    val purchased: Boolean,
    val sku: String,
    val kind: String,
    @SerializedName("expires_at") val expiresAt: String?,
    @SerializedName("heart_balance") val heartBalance: Int,
)
