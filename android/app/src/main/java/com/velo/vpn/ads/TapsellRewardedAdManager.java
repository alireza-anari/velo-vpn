package com.velo.vpn.ads;

import android.app.Activity;

import androidx.annotation.NonNull;

import ir.tapsell.mediation.Tapsell;
import ir.tapsell.mediation.ad.AdStateListener;
import ir.tapsell.mediation.ad.request.RequestResultListener;
import ir.tapsell.mediation.ad.show.AdShowCompletionState;

/**
 * Thin adapter around the current Tapsell Mediation rewarded-ad API.
 *
 * The Tapsell app key is supplied at build time through the manifest placeholder
 * TapsellMediationAppKey. The rewarded zone id is supplied by Velo remote config,
 * so the business reward can be adjusted without releasing a new APK.
 */
public final class TapsellRewardedAdManager {
    public interface Callback {
        void onRewarded(String responseId);
        void onError(String message);
    }

    public void show(Activity activity, String zoneId, Callback callback) {
        if (zoneId == null || zoneId.isBlank()) {
            callback.onError("tapsell_not_configured");
            return;
        }

        Tapsell.requestRewardedAd(zoneId, new RequestResultListener() {
            @Override
            public void onSuccess(@NonNull String adId) {
                if (activity.isFinishing() || activity.isDestroyed()) return;
                showLoaded(activity, adId, callback);
            }

            @Override
            public void onFailure(@NonNull String message) {
                callback.onError(message);
            }
        });
    }

    private void showLoaded(Activity activity, String responseId, Callback callback) {
        Tapsell.showRewardedAd(responseId, activity, new AdStateListener.Rewarded() {
            private boolean rewarded;
            private boolean terminalCallbackSent;

            @Override
            public void onAdClicked() {
                // Never reward clicks. Reward is granted only from onRewarded().
            }

            @Override
            public void onAdImpression() {
                // Impression analytics are handled by the provider.
            }

            @Override
            public void onRewarded() {
                if (rewarded || terminalCallbackSent) return;
                rewarded = true;
                terminalCallbackSent = true;
                callback.onRewarded(responseId);
            }

            @Override
            public void onAdClosed(@NonNull AdShowCompletionState completionState) {
                if (!rewarded && !terminalCallbackSent) {
                    terminalCallbackSent = true;
                    callback.onError("ad_closed_without_reward");
                }
            }

            @Override
            public void onAdFailed(@NonNull String message) {
                if (terminalCallbackSent) return;
                terminalCallbackSent = true;
                callback.onError(message.isBlank() ? "ad_show_failed" : message);
            }
        });
    }
}
