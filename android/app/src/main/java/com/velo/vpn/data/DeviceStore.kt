package com.velo.vpn.data

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.first
import java.security.KeyStore
import java.util.UUID
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

private val Context.veloDataStore by preferencesDataStore(name = "velo_session")

class DeviceStore(private val context: Context) {
    private val installIdKey = stringPreferencesKey("install_id")
    // Legacy DataStore token keys are retained only for one-time migration.
    private val legacyDeviceTokenKey = stringPreferencesKey("device_token")
    private val legacyUserTokenKey = stringPreferencesKey("user_token")
    private val secure = KeystoreStringStore(context)

    suspend fun installId(): String {
        val existing = context.veloDataStore.data.first()[installIdKey]
        if (!existing.isNullOrBlank()) return existing
        val generated = UUID.randomUUID().toString() + UUID.randomUUID().toString()
        context.veloDataStore.edit { it[installIdKey] = generated }
        return generated
    }

    suspend fun deviceToken(): String? = secure.get("device_token") ?: migrateLegacy(legacyDeviceTokenKey, "device_token")
    suspend fun userToken(): String? = secure.get("user_token") ?: migrateLegacy(legacyUserTokenKey, "user_token")

    suspend fun saveDeviceToken(token: String) {
        secure.put("device_token", token)
        context.veloDataStore.edit { it.remove(legacyDeviceTokenKey) }
    }

    suspend fun saveUserToken(token: String?) {
        if (token == null) secure.remove("user_token") else secure.put("user_token", token)
        context.veloDataStore.edit { it.remove(legacyUserTokenKey) }
    }

    private suspend fun migrateLegacy(key: androidx.datastore.preferences.core.Preferences.Key<String>, secureKey: String): String? {
        val old = context.veloDataStore.data.first()[key] ?: return null
        secure.put(secureKey, old)
        context.veloDataStore.edit { it.remove(key) }
        return old
    }
}

/** Small Android Keystore-backed store for bearer tokens. The install id is deliberately not secret. */
private class KeystoreStringStore(context: Context) {
    private val prefs = context.getSharedPreferences("velo_secure", Context.MODE_PRIVATE)
    private val alias = "velo_session_key_v1"
    private val keyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }

    private fun key(): SecretKey {
        val existing = keyStore.getKey(alias, null) as? SecretKey
        if (existing != null) return existing
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        generator.init(
            KeyGenParameterSpec.Builder(
                alias,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build()
        )
        return generator.generateKey()
    }

    fun put(name: String, value: String) {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val encoded = Base64.encodeToString(cipher.iv, Base64.NO_WRAP) + ":" +
            Base64.encodeToString(cipher.doFinal(value.toByteArray(Charsets.UTF_8)), Base64.NO_WRAP)
        prefs.edit().putString(name, encoded).apply()
    }

    fun get(name: String): String? {
        val encoded = prefs.getString(name, null) ?: return null
        return try {
            val parts = encoded.split(":", limit = 2)
            if (parts.size != 2) return null
            val iv = Base64.decode(parts[0], Base64.NO_WRAP)
            val ciphertext = Base64.decode(parts[1], Base64.NO_WRAP)
            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, iv))
            String(cipher.doFinal(ciphertext), Charsets.UTF_8)
        } catch (_: Exception) {
            // Keystore keys can be invalidated after some device security changes. Force re-authentication safely.
            prefs.edit().remove(name).apply()
            null
        }
    }

    fun remove(name: String) {
        prefs.edit().remove(name).apply()
    }
}
