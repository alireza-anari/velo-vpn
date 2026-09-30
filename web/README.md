# Velo Web

نسخه وب Velo با React + TypeScript + Vite.

## معماری API

در Production وب و API پشت یک Origin قرار می‌گیرند و Frontend مستقیماً از مسیرهای `/v1` استفاده می‌کند. بنابراین IP سرور Backend داخل Bundle قرار نمی‌گیرد.

در Development، Vite مسیرهای `/v1` و `/health` را به `VELO_DEV_API_TARGET` Proxy می‌کند.

## اجرا

```bash
cp .env.example .env
npm install
npm run dev
```

Backend باید روی آدرس تنظیم‌شده در `.env` فعال باشد.

## بررسی کیفیت

```bash
npm run check
```

هیچ Secret نباید در متغیرهای `VITE_*` یا کد Client قرار بگیرد؛ هر متغیری که به Browser Bundle برسد عمومی محسوب می‌شود.
