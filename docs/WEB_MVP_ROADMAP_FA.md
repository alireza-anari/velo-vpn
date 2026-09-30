# نقشه راه Velo Web MVP

این سند مسیر توسعه نسخه وب Velo را مرحله‌بندی می‌کند. اصل کار این است که هر مرحله فقط وقتی تمام‌شده محسوب شود که معیارهای پذیرش همان مرحله کامل و CI سبز باشد.

## اصول ثابت

- وب‌اپ RTL و Mobile-first است و روی Android، iPhone و Desktop کار می‌کند.
- اتصال VPN توسط WireGuard یا کلاینت سازگار انجام می‌شود؛ وب‌اپ حساب، اعتبار، اشتراک و کانفیگ را مدیریت می‌کند.
- هر کاربر دسترسی VPN اختصاصی دارد و اشتراک‌گذاری یک Peer بین کاربران ممنوع است.
- هیچ Secret، Private Key سرور، Admin Key یا Agent Token به مرورگر ارسال نمی‌شود.
- API در Production از همان Origin یا پشت Reverse Proxy در دسترس است تا تغییر VPS مرکزی نیاز به Build مجدد وب‌اپ نداشته باشد.
- Android فعلی حذف نمی‌شود، اما توسعه Native تا بعد از تثبیت Web MVP متوقف می‌ماند.

## مرحله ۱ — Foundation + Authentication

هدف: پایه تولیدی وب‌اپ و ورود امن با ایمیل.

خروجی‌ها:
- React + TypeScript + Vite
- ساختار Feature-based
- Design Tokens و Light/Dark
- RTL و Responsive پایه
- API Client یکپارچه
- OTP Login
- Session وب با Cookie از نوع HttpOnly
- Logout و بازیابی Session
- PWA manifest پایه
- Build / Typecheck / Lint در CI

معیار پایان:
- کاربر می‌تواند ایمیل را وارد کند، OTP را تأیید کند، وارد ناحیه کاربری شود، صفحه را Refresh کند و همچنان Login بماند، سپس Logout کند.
- Token در localStorage/sessionStorage ذخیره نشود.
- Backend و Web CI سبز باشند.

## مرحله ۲ — VPN Access + Welcome Credit

هدف: هر کاربر بعد از ثبت‌نام یک دسترسی WireGuard اختصاصی و ۱۵ دقیقه اعتبار هدیه داشته باشد.

خروجی‌ها:
- مدل VPN Access دائمی برای User
- Peer lifecycle مستقل از Android session
- Welcome credit قابل تنظیم از Admin
- QR و فایل conf اختصاصی
- فعال/غیرفعال شدن Peer بر اساس اعتبار
- تست End-to-End با Node خارجی

## مرحله ۳ — Free Wallet + Rewarded Ads

هدف: کاربر Free با مشاهده تبلیغ، زمان واقعی VPN دریافت کند.

خروجی‌ها:
- Time Wallet بر حسب ثانیه
- کسر اعتبار فقط هنگام مصرف واقعی VPN
- Daily reward limit
- Challenge/verification سمت Backend
- اتصال Provider تبلیغاتی وب با Server-to-Server verification در صورت پشتیبانی
- تنظیم مقدار جایزه و سقف روزانه از Admin

## مرحله ۴ — Premium + Payment

هدف: فروش واقعی اشتراک.

خروجی‌ها:
- پلن‌های ۱۵ روز، ۱ ماه، ۳ ماه و ۶ ماه
- کارت‌به‌کارت و Upload رسید
- Pending/Approved/Rejected
- فعال‌سازی فوری Peer بعد از تأیید
- تمدید اشتراک بدون تعویض کانفیگ
- تاریخچه پرداخت کاربر

## مرحله ۵ — Account + Usage + Server Switch

هدف: پنل کامل Self-service.

خروجی‌ها:
- مصرف روز/ماه
- وضعیت Free/Premium
- Reset کانفیگ با ابطال Peer قبلی
- تغییر لوکیشن و صدور کانفیگ جدید
- محدودیت تعویض سرور برای جلوگیری از Abuse
- راهنمای Import برای iOS/Android/Desktop

## مرحله ۶ — Admin + Node Operations

هدف: عملیات روزانه بدون SSH برای کارهای عادی.

خروجی‌ها:
- مدیریت کاربر/اشتراک/پرداخت
- مشاهده Peer و مصرف
- Suspend/Reset دسترسی
- مدیریت Nodeها، Health و Capacity
- Routing و Failover
- Audit log کامل

## مرحله ۷ — Production Hardening

هدف: آماده فروش عمومی.

خروجی‌ها:
- Domain + HTTPS
- Reverse proxy و Security headers
- Backup/restore تست‌شده
- Rate limiting و Abuse controls
- Monitoring/alerts
- Privacy/Terms
- Deployment runbook
- تست بار و سناریوی خرابی Node/API
