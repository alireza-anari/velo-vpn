# Velo Android / Google Play release checklist

## Account / publisher
- Use a legitimate publisher structure whose identity, country, payment profile and ongoing verification can be maintained.
- Keep the package name, app signing key, brand/domain and backend under Velo's control.

## VPN policy preparation
- VPN is the app's primary functionality.
- Complete the Play Console VpnService declaration requested by Google at submission time.
- Prepare a short review video showing the in-app flow and VPN connection.
- Confirm the final merged manifest and behavior do not manipulate third-party traffic for ad monetization.

## Privacy / Data Safety
- Host `/legal/privacy` and `/legal/terms` on the production HTTPS domain.
- Replace the draft contact address and effective date.
- Review the final Tapsell SDK/adapters and complete Data Safety from observed behavior, not assumptions.
- Verify no browsing history or destination logging exists in server/node logs.

## Build / security
- `VELO_API_BASE_URL` must be HTTPS for release builds.
- Supply the real `VELO_TAPSELL_APP_KEY` through CI/secret build properties.
- Keep the Android signing key outside source control and back it up securely.
- Run the CI release candidate build and inspect the merged manifest/permissions.
- Test guest flow, rewarded ad, free timer, speed limit, Premium takeover, server selection, manual payment and receipt approval on physical Android devices.

## Store listing
- Use the approved Velo logo and the minimal lilac/purple visual language.
- Clearly explain that Free has time/speed limits and Premium removes Velo-imposed time/speed limits.
- Avoid promising an absolute connection speed or uninterrupted availability.
