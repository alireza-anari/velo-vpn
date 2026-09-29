package com.velo.vpn.data

import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path

interface VeloApi {
    @GET("v1/config/public")
    suspend fun publicConfig(): PublicConfig

    @POST("v1/guest")
    suspend fun guest(@Body request: GuestRequest): GuestResponse


    @POST("v1/auth/request-otp")
    suspend fun requestOtp(@Body request: OtpRequestBody): OtpRequestResponse

    @POST("v1/auth/verify-otp")
    suspend fun verifyOtp(@Body request: OtpVerifyBody): AuthResponse

    @POST("v1/auth/link-device")
    suspend fun linkDevice(@Header("Authorization") auth: String, @Body request: LinkDeviceBody): Map<String, Any>

    @POST("v1/auth/unlink-device")
    suspend fun unlinkDevice(@Header("Authorization") auth: String, @Body request: LinkDeviceBody): Map<String, Any>

    @GET("v1/auth/me")
    suspend fun me(@Header("Authorization") auth: String): MeResponse

    @GET("v1/users/me/hearts")
    suspend fun hearts(@Header("Authorization") auth: String): HeartsResponse

    @GET("v1/users/me/subscription")
    suspend fun subscription(@Header("Authorization") auth: String): SubscriptionResponse

    @GET("v1/reports/summary")
    suspend fun report(@Header("Authorization") auth: String): ReportSummary

    @GET("v1/missions/today")
    suspend fun missionsToday(@Header("Authorization") auth: String): MissionTodayResponse

    @POST("v1/missions/claim/{missionKey}")
    suspend fun claimMission(@Header("Authorization") auth: String, @Path("missionKey") missionKey: String): MissionClaimResponse

    @GET("v1/missions/weekly")
    suspend fun missionsWeekly(@Header("Authorization") auth: String): WeeklyMissionsResponse

    @POST("v1/missions/claim-week/{missionKey}")
    suspend fun claimWeeklyMission(@Header("Authorization") auth: String, @Path("missionKey") missionKey: String): MissionClaimResponse

    @GET("v1/missions/one-time")
    suspend fun oneTimeMissions(@Header("Authorization") auth: String): OneTimeMissionsResponse

    @POST("v1/missions/open/{missionKey}")
    suspend fun openOneTimeMission(@Header("Authorization") auth: String, @Path("missionKey") missionKey: String): MissionOpenResponse

    @POST("v1/missions/claim-once/{missionKey}")
    suspend fun claimOneTimeMission(@Header("Authorization") auth: String, @Path("missionKey") missionKey: String): MissionClaimResponse

    @GET("v1/referrals/me")
    suspend fun referrals(@Header("Authorization") auth: String): ReferralSummary

    @Multipart
    @POST("v1/payments/manual")
    suspend fun manualPayment(
        @Header("Authorization") auth: String,
        @Part("kind") kind: RequestBody,
        @Part("amount_toman") amountToman: RequestBody,
        @Part("plan_code") planCode: RequestBody?,
        @Part("requested_hearts") requestedHearts: RequestBody,
        @Part receipt: MultipartBody.Part,
    ): PaymentCreated

    @GET("v1/payments/mine")
    suspend fun myPayments(@Header("Authorization") auth: String): List<PaymentItem>


    @GET("v1/store/catalog")
    suspend fun storeCatalog(@Header("Authorization") auth: String): StoreCatalogResponse

    @POST("v1/store/purchase/{sku}")
    suspend fun purchaseStoreItem(@Header("Authorization") auth: String, @Path("sku") sku: String): StorePurchaseResponse

    @GET("v1/rewards/free-status")
    suspend fun freeStatus(@Header("Authorization") auth: String): FreeStatus

    @POST("v1/rewards/ad-challenge")
    suspend fun adChallenge(@Header("Authorization") auth: String): AdChallengeResponse

    @POST("v1/rewards/ad-complete")
    suspend fun adComplete(
        @Header("Authorization") auth: String,
        @Body request: AdCompleteRequest,
    ): AdCompleteResponse

    @GET("v1/vpn/status")
    suspend fun vpnStatus(@Header("Authorization") auth: String): VpnStatusResponse

    @POST("v1/vpn/connect")
    suspend fun vpnConnect(
        @Header("Authorization") auth: String,
        @Body request: VpnConnectRequest,
    ): VpnConnectResponse

    @POST("v1/vpn/disconnect/{sessionId}")
    suspend fun vpnDisconnect(
        @Header("Authorization") auth: String,
        @Path("sessionId") sessionId: Long,
    ): Map<String, Any>

    @POST("v1/vpn/heartbeat/{sessionId}")
    suspend fun vpnHeartbeat(
        @Header("Authorization") auth: String,
        @Path("sessionId") sessionId: Long,
    ): VpnHeartbeatResponse

    @GET("v1/vpn/servers")
    suspend fun servers(@Header("Authorization") auth: String): List<ServerDto>
}
