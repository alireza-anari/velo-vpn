package com.velo.vpn

import android.app.Application
import com.velo.vpn.core.AppContainer
import com.velo.vpn.diagnostics.CrashStore

class VeloApplication : Application() {
    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        CrashStore(this).install()
        container = AppContainer(this)
    }
}
