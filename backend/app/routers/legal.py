from __future__ import annotations

from html import escape

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from ..config import settings

router = APIRouter(tags=["legal"])


def _layout(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        f"""<!doctype html><html lang=\"fa\" dir=\"rtl\"><head><meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>{escape(title)} - Velo</title>
<style>body{{font-family:system-ui,-apple-system,sans-serif;max-width:760px;margin:40px auto;padding:0 20px;line-height:2;color:#242033;background:#faf9ff}}h1,h2{{color:#352a5b}}.card{{background:white;border:1px solid #eee9ff;border-radius:20px;padding:24px;box-shadow:0 8px 30px #6f4cff0d}}small{{color:#777}}</style></head>
<body><div class=\"card\"><h1>{escape(title)}</h1>{body}<hr><small>تاریخ اجرا: {escape(settings.legal_effective_date)} • تماس: {escape(settings.legal_contact_email)}</small></div></body></html>"""
    )


@router.get("/legal/privacy", response_class=HTMLResponse, include_in_schema=False)
def privacy_policy():
    body = """
<p>Velo برای ارائه سرویس VPN، فقط داده‌هایی را که برای کارکرد سرویس لازم است نگهداری می‌کند.</p>
<h2>داده‌هایی که ممکن است نگهداری شوند</h2>
<ul>
<li>شناسه نصب ناشناس و اطلاعات فنی لازم برای مدیریت اعتبار زمانی و جلوگیری از سوءاستفاده.</li>
<li>ایمیل، فقط زمانی که خودتان برای Premium، حمایت یا ذخیره مزایا حساب می‌سازید.</li>
<li>اطلاعات عملیاتی اتصال مانند زمان شروع/پایان، میزان کلی دریافت و ارسال و سرور انتخاب‌شده.</li>
<li>رسید پرداخت کارت‌به‌کارت تا زمانی که برای بررسی و امور مالی لازم باشد.</li>
<li>اطلاعات مربوط به قلب‌ها، مأموریت‌ها، دعوت دوستان و وضعیت اشتراک.</li>
</ul>
<h2>چیزی که Velo ذخیره نمی‌کند</h2>
<p>Velo تاریخچه وب‌سایت‌های بازدیدشده، محتوای ترافیک، پیام‌ها یا فهرست مقصدهای اینترنتی شما را برای پروفایل‌سازی نگهداری نمی‌کند.</p>
<h2>تبلیغات</h2>
<p>نسخه رایگان از تبلیغات جایزه‌ای استفاده می‌کند. ارائه‌دهنده تبلیغ ممکن است مطابق سیاست حریم خصوصی خودش اطلاعات فنی یا شناسه‌های تبلیغاتی را پردازش کند.</p>
<h2>امنیت و نگهداری</h2>
<p>دسترسی مدیریتی محدود است، توکن‌ها در اپ با Android Keystore محافظت می‌شوند و رسیدهای پرداخت به‌صورت خصوصی نگهداری می‌شوند. داده‌ها فقط تا زمانی که برای ارائه سرویس، امنیت، حسابداری یا تعهدات قانونی لازم باشند نگهداری می‌شوند.</p>
<h2>حقوق شما</h2>
<p>برای درخواست دسترسی، اصلاح یا حذف داده‌های حساب می‌توانید از ایمیل تماس پایین صفحه استفاده کنید. حذف حساب ممکن است اطلاعاتی را که نگهداری آن برای تسویه یا الزامات قانونی ضروری است فوراً حذف نکند.</p>
"""
    return _layout("حریم خصوصی Velo", body)


@router.get("/legal/terms", response_class=HTMLResponse, include_in_schema=False)
def terms_of_service():
    body = """
<p>با استفاده از Velo، این شرایط را می‌پذیرید. این متن برای نسخه اولیه سرویس است و پیش از انتشار عمومی باید با شرایط حقوقی محل فعالیت شما بازبینی شود.</p>
<h2>سرویس رایگان و Premium</h2>
<p>نسخه رایگان دارای محدودیت زمان و سرعت است. Premium محدودیت زمانی و محدودیت سرعت اعمال‌شده از طرف Velo ندارد، اما سرعت واقعی به اینترنت کاربر، مسیر شبکه و ظرفیت زیرساخت بستگی دارد. هر حساب Premium فقط یک اتصال VPN هم‌زمان دارد.</p>
<h2>پرداخت دستی</h2>
<p>در نسخه فعلی، پرداخت کارت‌به‌کارت پس از بارگذاری رسید و تأیید ادمین فعال می‌شود. بارگذاری رسید به‌تنهایی به معنی تأیید پرداخت نیست.</p>
<h2>قلب‌ها و مزایا</h2>
<p>قلب‌ها اعتبار وفاداری داخل Velo هستند، ارزش نقدی یا قابلیت برداشت ندارند و فقط برای مزایا و تخفیف‌های داخل سرویس قابل استفاده‌اند. سقف تخفیف Premium طبق تنظیمات محصول اعمال می‌شود.</p>
<h2>استفاده مجاز</h2>
<p>استفاده از سرویس برای سوءاستفاده از شبکه، حمله، ارسال هرزنامه، فروش مجدد غیرمجاز، اتوماسیون مخرب یا فعالیتی که قوانین قابل اعمال یا شرایط ارائه‌دهندگان زیرساخت را نقض کند مجاز نیست.</p>
<h2>دسترس‌پذیری</h2>
<p>Velo برای پایداری سرویس تلاش می‌کند اما دسترسی دائمی، IP ثابت یا سرعت مشخص را مگر در محصولی که صراحتاً چنین ویژگی‌ای دارد تضمین نمی‌کند.</p>
"""
    return _layout("شرایط استفاده از Velo", body)
