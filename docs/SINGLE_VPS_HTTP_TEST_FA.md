# استقرار تستی Velo روی یک VPS

این حالت فقط برای تست Phase 2 است. همان VPS هم Control Plane است و هم VPN Node.

## معماری

- Nginx روی پورت 80: وب‌اپ و Reverse Proxy
- FastAPI فقط روی 127.0.0.1:8000
- PostgreSQL محلی
- WireGuard روی UDP 51820
- Node Agent فقط روی 127.0.0.1:8787
- UFW در اسکریپت خودکار فعال نمی‌شود تا SSH از راه دور قطع نشود.

## نکته امنیتی

در تست بدون دامنه و HTTPS، `ENVIRONMENT=development` است تا Cookie روی HTTP کار کند و OTP تستی در UI نمایش داده شود. این حالت برای فروش عمومی مناسب نیست.

قبل از فروش:
1. دامنه و HTTPS فعال شود.
2. `ENVIRONMENT=production` شود.
3. SMTP واقعی تنظیم شود.
4. OTP دیگر در پاسخ API نمایش داده نشود.
5. UFW بعد از تأیید SSH دوم فعال شود.

Secretها فقط در `/opt/velo/backend/.env` روی سرور هستند و نباید در GitHub یا چت قرار بگیرند.
