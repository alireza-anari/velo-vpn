package com.velo.vpn.data

import android.content.Context
import com.android.installreferrer.api.InstallReferrerClient
import com.android.installreferrer.api.InstallReferrerStateListener
import com.android.installreferrer.api.InstallReferrerClient.InstallReferrerResponse
import kotlinx.coroutines.suspendCancellableCoroutine
import java.net.URLDecoder
import kotlin.coroutines.resume

class ReferralAttribution(context: Context) {
    private val appContext = context.applicationContext

    suspend fun readReferralCode(): String? = suspendCancellableCoroutine { cont ->
        val client = InstallReferrerClient.newBuilder(appContext).build()
        cont.invokeOnCancellation { runCatching { client.endConnection() } }
        client.startConnection(object : InstallReferrerStateListener {
            override fun onInstallReferrerSetupFinished(responseCode: Int) {
                val code = if (responseCode == InstallReferrerResponse.OK) {
                    runCatching {
                        val raw = client.installReferrer.installReferrer.orEmpty()
                        parse(raw)
                    }.getOrNull()
                } else null
                runCatching { client.endConnection() }
                if (cont.isActive) cont.resume(code)
            }

            override fun onInstallReferrerServiceDisconnected() {
                runCatching { client.endConnection() }
                if (cont.isActive) cont.resume(null)
            }
        })
    }

    private fun parse(raw: String): String? {
        if (raw.isBlank()) return null
        val decoded = URLDecoder.decode(raw, Charsets.UTF_8.name())
        val pairs = decoded.split('&').mapNotNull {
            val i = it.indexOf('=')
            if (i <= 0) null else it.substring(0, i) to it.substring(i + 1)
        }.toMap()
        val code = pairs["referral_code"] ?: pairs["ref"] ?: pairs["code"]
        return code?.trim()?.uppercase()?.takeIf { it.matches(Regex("[A-Z0-9]{4,20}")) }
    }
}
