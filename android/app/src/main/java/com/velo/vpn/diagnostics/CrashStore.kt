package com.velo.vpn.diagnostics

import android.content.Context
import java.security.MessageDigest

/**
 * Privacy-preserving local crash breadcrumb.
 *
 * Velo intentionally does not upload stack traces in the MVP. We store only a short
 * fingerprint and app-package frames on-device so a user can include an incident id
 * in a support email if the app crashed previously.
 */
class CrashStore(private val context: Context) {
    private val prefs = context.getSharedPreferences("velo_diagnostics", Context.MODE_PRIVATE)

    data class CrashInfo(val incidentId: String, val timestampMs: Long)

    fun install() {
        val previous = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { thread, throwable ->
            runCatching { remember(throwable) }
            previous?.uncaughtException(thread, throwable)
        }
    }

    fun lastCrash(): CrashInfo? {
        val incident = prefs.getString("last_incident_id", null) ?: return null
        val timestamp = prefs.getLong("last_timestamp_ms", 0L)
        // Breadcrumbs older than 14 days are not useful and are removed locally.
        if (timestamp <= 0L || System.currentTimeMillis() - timestamp > 14L * 24 * 60 * 60 * 1000) {
            clear()
            return null
        }
        return CrashInfo(incident, timestamp)
    }

    fun clear() {
        prefs.edit().clear().apply()
    }

    private fun remember(t: Throwable) {
        val safeFrames = t.stackTrace
            .asSequence()
            .filter { it.className.startsWith("com.velo.vpn") }
            .take(8)
            .joinToString("|") { "${it.className}.${it.methodName}:${it.lineNumber}" }
        val seed = "${t.javaClass.name}|$safeFrames"
        val digest = MessageDigest.getInstance("SHA-256").digest(seed.toByteArray())
        val incident = digest.take(6).joinToString("") { "%02x".format(it) }.uppercase()
        prefs.edit()
            .putString("last_incident_id", incident)
            .putLong("last_timestamp_ms", System.currentTimeMillis())
            .apply()
    }
}
