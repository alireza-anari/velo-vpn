# Velo — Frozen Product Decisions (MVP)

## Brand
- Name: **Velo**
- Personality: friendly, warm, minimal
- Primary visual language: light UI, lilac + soft purple
- Dark mode supported
- Logo: abstract V / connection / heart mark

## Main navigation
1. خانه
2. هدایا
3. گزارش
4. تنظیمات

## Guest-first usage
- No account required for free VPN usage.
- Guest can watch a rewarded video, receive time, connect, and leave.
- Guest uses an anonymous install/session ID only; no phone number is collected.
- Account is required only for durable value: Premium, support payments, hearts persistence, referral identity, account recovery.
- Account login uses **email + 6-digit OTP**. No phone number.

## Free tier
- Limited by **time** and **speed**.
- No volume cap shown to user.
- Rewarded ad adds time; exact minutes and speed are remote-configurable.
- Current business placeholder: 2 Mbps and 20–30 minutes per completed rewarded video, to be finalized after real Tapsell eCPM data.
- Ad-earned time expires/reset daily.
- No product-side limit on how many ads the user may choose to watch, subject to ad inventory/anti-abuse controls.

## Premium
- No time limit.
- No speed throttling by Velo (actual speed depends on network/server).
- No volume limit for normal consumer usage.
- No ads.
- One active VPN session per Premium account at a time.
- Account can be logged into on multiple devices; only one can have an active VPN tunnel simultaneously.

### Premium prices
- 15 days: **189,000 toman**
- 1 month: **349,000 toman**
- 3 months: **949,000 toman**
- 6 months: **1,749,000 toman**
- Heart-based discount cap: **30%**
- 3-month plan is the recommended plan in UI.

## Hearts
- Loyalty currency; not cash and not withdrawable/transferable.
- Used for Premium discounts now.
- Future store can use hearts for VIP servers, static IP, temporary free-tier speed boosts, visual themes/badges, and other entitlements.
- Premium discount tiers are remote configurable, hard capped at 30%.

## Missions
- Easy, low-friction missions.
- Daily missions should naturally encourage an active free user to watch at least **one extra rewarded video** if they want the full daily bonus.
- Example mission types: first connection, 15 minutes use, 1 rewarded video, 2 rewarded videos, daily completion bonus, streaks.
- One-time missions can include Instagram follow and Telegram join; rewards are remote configurable.
- Never reward ad clicks or incentivized ratings/reviews.

## Referrals
- Install gives inviter a reward.
- Genuine daily use by invited user gives inviter another reward for a limited initial period (target: first 7 days).
- Daily use should mean actual VPN usage, not merely opening the app.
- Referral screen shows install reward, daily progress and each invitee's day/status.

## Support project
- User may financially support Velo.
- Support grants hearts as a thank-you reward.
- MVP payment method: card-to-card transfer + receipt upload.
- Admin receives notice, reviews receipt, and manually approves/rejects.
- After approval, Premium/heart rewards are applied automatically by backend.
- Card/account details are remote-configurable; not hard-coded in APK.
- Future payment gateways can be added alongside/replacing manual transfer.

## Servers
- Free user sees only **Best Server** and Velo selects automatically.
- Premium user can select country/server.
- Future VIP/static-IP servers appear as locked/entitled items.

## Privacy
- Do not store browsing history, visited websites, DNS destinations or traffic contents.
- Store only operational data needed for session, reward, subscription, referral, payment and anti-abuse functions.

## Store implementation notes (Milestone 3)
- Store is now architected as a server-side entitlement system rather than hard-coded UI unlocks.
- Initial catalog types: VIP server access, temporary Free speed boost, cosmetics; static IP is present but disabled until provisioning exists.
- Heart purchases are durable ledger transactions and cannot produce a negative balance.
- Store catalog/prices/durations are remote-configurable from backend settings.
- VIP access can be scoped by country; initial example SKU targets US VIP servers for 30 days.
