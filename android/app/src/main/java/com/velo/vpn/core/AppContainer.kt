package com.velo.vpn.core

import android.app.Application
import com.google.gson.Gson
import okhttp3.logging.HttpLoggingInterceptor
import com.velo.vpn.BuildConfig
import com.velo.vpn.ads.TapsellRewardedAdManager
import com.velo.vpn.data.DeviceStore
import com.velo.vpn.data.ReferralAttribution
import com.velo.vpn.data.VeloApi
import com.velo.vpn.data.VeloRepository
import com.velo.vpn.vpn.WireGuardTunnelManager
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

class AppContainer(application: Application) {
    private val gson = Gson()
    private val logging = HttpLoggingInterceptor().apply {
        level = if (BuildConfig.DEBUG) HttpLoggingInterceptor.Level.BASIC else HttpLoggingInterceptor.Level.NONE
    }
    private val http = OkHttpClient.Builder()
        .connectTimeout(12, TimeUnit.SECONDS)
        .readTimeout(35, TimeUnit.SECONDS)
        .writeTimeout(35, TimeUnit.SECONDS)
        .callTimeout(45, TimeUnit.SECONDS)
        .retryOnConnectionFailure(true)
        .addInterceptor { chain ->
            val request = chain.request().newBuilder()
                .header("User-Agent", "Velo-Android/${BuildConfig.VERSION_NAME}")
                .header("X-Velo-Version", BuildConfig.VERSION_NAME)
                .build()
            chain.proceed(request)
        }
        .addInterceptor(logging)
        .build()

    private val retrofit = Retrofit.Builder()
        .baseUrl(BuildConfig.API_BASE_URL)
        .client(http)
        .addConverterFactory(GsonConverterFactory.create(gson))
        .build()

    private val api = retrofit.create(VeloApi::class.java)
    val store = DeviceStore(application)
    val referralAttribution = ReferralAttribution(application)
    val repository = VeloRepository(api, store, gson)
    val tunnelManager = WireGuardTunnelManager(application)
    val rewardedAds = TapsellRewardedAdManager()
}
