# Google Play Data Safety working notes

This is a release-preparation worksheet, not a completed Play Console declaration. Re-check it against the exact SDK versions and product behavior immediately before submission.

## Velo first-party data
Likely collected/processed when relevant:
- Email address: account login/recovery only; optional until account-requiring actions.
- App activity/product interaction: missions, rewards, referrals, subscription state.
- Payment evidence: manually uploaded receipt image for the MVP payment flow.
- App/device identifiers: anonymous install identifier for free credit, anti-abuse and device linking.
- VPN operational metadata: session timestamps, aggregate bytes, selected Velo server, connection status.

Velo product intent is **not** to collect browsing history, destination websites, packet content or DNS history.

## Third-party SDK review before release
Tapsell Mediation and every enabled adapter must be reviewed for:
- advertising ID/device identifiers;
- diagnostics and interaction data;
- data sharing with ad networks;
- consent requirements;
- permissions merged into the final manifest.

Do not complete the Play declaration from this document alone. Inspect the final merged manifest and each active ad adapter's current data disclosure.
