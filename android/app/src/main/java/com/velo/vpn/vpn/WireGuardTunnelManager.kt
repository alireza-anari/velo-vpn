package com.velo.vpn.vpn

import android.content.Context
import com.velo.vpn.data.VpnConnectResponse
import com.wireguard.android.backend.GoBackend
import com.wireguard.android.backend.Tunnel
import com.wireguard.config.Config
import com.wireguard.crypto.KeyPair
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.ByteArrayInputStream

class WireGuardTunnelManager(context: Context) {
    private val backend = GoBackend(context.applicationContext)
    private val tunnel = VeloTunnel()
    private var pendingKeyPair: KeyPair? = null

    fun prepareClientPublicKey(): String {
        val pair = KeyPair()
        pendingKeyPair = pair
        return pair.publicKey.toBase64()
    }

    suspend fun connect(remote: VpnConnectResponse) = withContext(Dispatchers.IO) {
        val pair = pendingKeyPair ?: error("client_key_not_prepared")
        val quickConfig = buildString {
            appendLine("[Interface]")
            appendLine("PrivateKey = ${pair.privateKey.toBase64()}")
            appendLine("Address = ${remote.clientAddress}")
            if (remote.dns.isNotBlank()) appendLine("DNS = ${remote.dns}")
            appendLine()
            appendLine("[Peer]")
            appendLine("PublicKey = ${remote.serverPublicKey}")
            appendLine("AllowedIPs = ${remote.allowedIps.joinToString(", ")}")
            appendLine("Endpoint = ${remote.endpoint}")
            appendLine("PersistentKeepalive = ${remote.persistentKeepalive}")
        }
        val config = Config.parse(ByteArrayInputStream(quickConfig.toByteArray(Charsets.UTF_8)))
        backend.setState(tunnel, Tunnel.State.UP, config)
        pendingKeyPair = null
    }

    suspend fun disconnect() = withContext(Dispatchers.IO) {
        backend.setState(tunnel, Tunnel.State.DOWN, null)
        pendingKeyPair = null
    }

    suspend fun isConnected(): Boolean = withContext(Dispatchers.IO) {
        runCatching { backend.getState(tunnel) == Tunnel.State.UP }.getOrDefault(false)
    }

    private class VeloTunnel : Tunnel {
        @Volatile private var state: Tunnel.State = Tunnel.State.DOWN
        override fun getName(): String = "velo"
        override fun onStateChange(newState: Tunnel.State) {
            state = newState
        }
    }
}
