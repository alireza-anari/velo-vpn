package com.velo.vpn.data

import com.google.gson.Gson
import kotlinx.coroutines.sync.Mutex
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import kotlinx.coroutines.sync.withLock
import retrofit2.HttpException
import java.util.UUID
import java.io.IOException
import kotlinx.coroutines.CancellationException

class VeloApiException(val code: Int, val apiDetail: String) : RuntimeException(apiDetail)

class VeloRepository(
    private val api: VeloApi,
    private val store: DeviceStore,
    private val gson: Gson,
) {
    private val deviceMutex = Mutex()

    suspend fun ensureDevice(referralCode: String? = null): String = deviceMutex.withLock {
        store.deviceToken()?.let { return@withLock it }
        val response = safeApi { api.guest(GuestRequest(store.installId(), referralCode)) }
        store.saveDeviceToken(response.deviceToken)
        response.deviceToken
    }

    suspend fun config(): PublicConfig = safeApi { api.publicConfig() }

    suspend fun isLoggedIn(): Boolean = !store.userToken().isNullOrBlank()

    suspend fun requestOtp(email: String): OtpRequestResponse = safeApi {
        api.requestOtp(OtpRequestBody(email.trim().lowercase()))
    }

    suspend fun verifyOtpAndLink(email: String, code: String): AuthResponse {
        val authResponse = safeApi { api.verifyOtp(OtpVerifyBody(email.trim().lowercase(), code.trim())) }
        store.saveUserToken(authResponse.accessToken)
        try {
            val deviceToken = ensureDevice()
            safeApi { api.linkDevice(bearer(authResponse.accessToken), LinkDeviceBody(deviceToken)) }
        } catch (t: Throwable) {
            store.saveUserToken(null)
            throw t
        }
        return authResponse
    }

    suspend fun me(): MeResponse = safeApi { api.me(userBearer()) }
    suspend fun hearts(): HeartsResponse = safeApi { api.hearts(userBearer()) }
    suspend fun subscription(): SubscriptionResponse = safeApi { api.subscription(userBearer()) }

    suspend fun logout() {
        val userToken = store.userToken() ?: return
        val deviceToken = ensureDevice()
        runCatching { safeApi { api.unlinkDevice(bearer(userToken), LinkDeviceBody(deviceToken)) } }
        store.saveUserToken(null)
    }

    suspend fun report(): ReportSummary = safeApi { api.report(bearer(ensureDevice())) }
    suspend fun missionsToday(): MissionTodayResponse = safeApi { api.missionsToday(bearer(ensureDevice())) }
    suspend fun claimMission(key: String): MissionClaimResponse = safeApi { api.claimMission(bearer(ensureDevice()), key) }
    suspend fun missionsWeekly(): WeeklyMissionsResponse = safeApi { api.missionsWeekly(bearer(ensureDevice())) }
    suspend fun claimWeeklyMission(key: String): MissionClaimResponse = safeApi { api.claimWeeklyMission(bearer(ensureDevice()), key) }
    suspend fun oneTimeMissions(): OneTimeMissionsResponse = safeApi { api.oneTimeMissions(bearer(ensureDevice())) }
    suspend fun openOneTimeMission(key: String): MissionOpenResponse = safeApi { api.openOneTimeMission(bearer(ensureDevice()), key) }
    suspend fun claimOneTimeMission(key: String): MissionClaimResponse = safeApi { api.claimOneTimeMission(bearer(ensureDevice()), key) }
    suspend fun referrals(): ReferralSummary = safeApi { api.referrals(userBearer()) }

    suspend fun submitManualPayment(
        kind: String,
        amountToman: Int,
        planCode: String?,
        requestedHearts: Int,
        fileName: String,
        mimeType: String,
        bytes: ByteArray,
    ): PaymentCreated = safeApi {
        val text = "text/plain".toMediaTypeOrNull()
        val fileBody = bytes.toRequestBody(mimeType.toMediaTypeOrNull())
        api.manualPayment(
            auth = userBearer(),
            kind = kind.toRequestBody(text),
            amountToman = amountToman.toString().toRequestBody(text),
            planCode = planCode?.toRequestBody(text),
            requestedHearts = requestedHearts.toString().toRequestBody(text),
            receipt = MultipartBody.Part.createFormData("receipt", fileName, fileBody),
        )
    }

    suspend fun myPayments(): List<PaymentItem> = safeApi { api.myPayments(userBearer()) }
    suspend fun storeCatalog(): StoreCatalogResponse = safeApi { api.storeCatalog(userBearer()) }
    suspend fun purchaseStoreItem(sku: String): StorePurchaseResponse = safeApi { api.purchaseStoreItem(userBearer(), sku) }

    suspend fun freeStatus(): FreeStatus = safeApi {
        api.freeStatus(bearer(ensureDevice()))
    }

    suspend fun vpnStatus(): VpnStatusResponse = safeApi {
        api.vpnStatus(bearer(ensureDevice()))
    }

    suspend fun connect(publicKey: String, serverId: Long?, forceTakeover: Boolean): VpnConnectResponse = safeApi {
        api.vpnConnect(
            bearer(ensureDevice()),
            VpnConnectRequest(publicKey, serverId, forceTakeover),
        )
    }

    suspend fun disconnect(sessionId: Long) = safeApi {
        api.vpnDisconnect(bearer(ensureDevice()), sessionId)
    }

    suspend fun heartbeat(sessionId: Long) = safeApi {
        api.vpnHeartbeat(bearer(ensureDevice()), sessionId)
    }

    suspend fun servers(): List<ServerDto> = safeApi {
        api.servers(bearer(ensureDevice()))
    }

    suspend fun createAdChallenge(): AdChallengeResponse = safeApi {
        api.adChallenge(bearer(ensureDevice()))
    }

    suspend fun completeAd(nonce: String, providerResponseId: String?): AdCompleteResponse = safeApi {
        api.adComplete(
            bearer(ensureDevice()),
            AdCompleteRequest(
                nonce = nonce,
                clientEventId = UUID.randomUUID().toString(),
                providerResponseId = providerResponseId,
            ),
        )
    }

    private suspend fun userBearer(): String {
        val token = store.userToken() ?: throw VeloApiException(401, "account_required")
        return bearer(token)
    }

    private fun bearer(token: String) = "Bearer $token"

    private suspend fun <T> safeApi(block: suspend () -> T): T {
        try {
            return block()
        } catch (e: CancellationException) {
            throw e
        } catch (e: HttpException) {
            val detail = try {
                val body = e.response()?.errorBody()?.string()
                if (body.isNullOrBlank()) null else gson.fromJson(body, ApiError::class.java)?.detail
            } catch (_: Exception) {
                null
            }
            throw VeloApiException(e.code(), detail ?: "server_error")
        } catch (e: IOException) {
            throw VeloApiException(0, "network_unavailable")
        }
    }
}
