import secrets

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from ..config import settings
from ..security import admin_session_token

router = APIRouter(tags=["admin-web"])

HTML = r'''<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Velo Admin</title>
<style>
:root{--p:#8b5cf6;--bg:#f7f5ff;--card:#fff;--text:#211a3a;--muted:#7e7892;--danger:#d84a6b}
*{box-sizing:border-box} body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Tahoma,sans-serif;background:var(--bg);color:var(--text)}
main{max-width:1120px;margin:auto;padding:24px}.top{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:20px}.brand{font-size:28px;font-weight:800}.pill{background:#eee8ff;border:0;border-radius:16px;padding:10px 14px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}.card{background:var(--card);border-radius:22px;padding:18px;box-shadow:0 5px 22px #6d5aa10d}.wide{grid-column:1/-1}h2{margin:0 0 14px;font-size:19px}.muted{color:var(--muted);font-size:13px}input,select,textarea{width:100%;padding:11px 12px;border:1px solid #e9e4f8;border-radius:12px;background:#fff;margin:5px 0 10px}button{border:0;border-radius:12px;padding:10px 14px;cursor:pointer;font-weight:700}.primary{background:var(--p);color:white}.ghost{background:#f2edff;color:#5f35c5}.danger{background:#fff0f4;color:var(--danger)}.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.payment{padding:14px 0;border-bottom:1px solid #f0edf6}.payment:last-child{border:0}.badge{font-size:11px;background:#f2edff;padding:5px 8px;border-radius:10px}.receipt{max-width:100%;max-height:500px;border-radius:16px;margin-top:10px}.hidden{display:none}.toast{position:fixed;left:20px;bottom:20px;background:#211a3a;color:#fff;padding:12px 16px;border-radius:12px;display:none}.small{font-size:12px}.server{padding:10px 0;border-bottom:1px solid #f0edf6}.server:last-child{border:0}.login{max-width:420px;margin:80px auto;background:#fff;padding:24px;border-radius:22px;box-shadow:0 5px 22px #6d5aa10d}.app-hidden{display:none}
</style>
</head><body>
<div id="login" class="login"><div class="brand">💜 Velo Admin</div><p class="muted">برای ورود رمز پنل را وارد کنید.</p><input id="password" type="password" placeholder="رمز پنل"><button class="primary" style="width:100%" onclick="login()">ورود امن</button></div>
<main id="app" class="app-hidden">
<div class="top"><div><div class="brand">💜 Velo Admin</div><div class="muted">پنل سبک MVP برای پرداخت‌ها، تنظیمات و سرورها</div></div><div class="row"><button class="ghost" onclick="logout()">خروج</button></div></div>
<div class="grid">
<section class="card wide"><div class="row" style="justify-content:space-between"><h2>پرداخت‌های در انتظار</h2><button class="ghost" onclick="loadPayments()">بروزرسانی</button></div><div id="payments" class="muted">برای مشاهده، کلید ادمین را وارد کنید.</div></section>
<section class="card"><h2>تنظیمات سریع</h2><label class="small">دقیقه پاداش هر ویدیو</label><input id="ad_reward_minutes" type="number"><label class="small">سرعت رایگان Mbps</label><input id="free_speed_mbps" type="number"><label class="small">Zone ID تپسل</label><input id="tapsell_rewarded_zone_id"><label class="small">شماره کارت</label><input id="manual_card_number"><label class="small">نام صاحب کارت</label><input id="manual_card_holder"><label class="small">Google Play URL</label><input id="android_store_url" placeholder="https://play.google.com/store/apps/details?id=..."><button class="primary" onclick="saveSettings()">ذخیره تنظیمات</button></section>
<section class="card"><h2>شبکه‌های اجتماعی</h2><label class="small">Instagram URL</label><input id="instagram_url"><label class="small">Telegram URL</label><input id="telegram_url"><button class="primary" onclick="saveSocial()">ذخیره ماموریت‌ها</button><p class="muted">تأیید Follow/Join در MVP به‌صورت soft open-and-claim است.</p></section>
<section class="card wide"><div class="row" style="justify-content:space-between"><h2>سرورها</h2><button class="ghost" onclick="loadServers()">بروزرسانی</button></div><div id="servers" class="muted">—</div></section>
</div></main><div id="toast" class="toast"></div>
<script>
function hdr(){return {'Content-Type':'application/json'}}
function toast(t){const e=document.getElementById('toast');e.textContent=t;e.style.display='block';setTimeout(()=>e.style.display='none',2400)}
async function login(){const password=document.getElementById('password').value;const r=await fetch('/admin/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password})});if(!r.ok){toast('رمز نادرست است');return}document.getElementById('login').style.display='none';document.getElementById('app').classList.remove('app-hidden');loadAll()}
async function logout(){await fetch('/admin/logout',{method:'POST'});document.getElementById('app').classList.add('app-hidden');document.getElementById('login').style.display='block'}
async function api(url,opt={}){const r=await fetch(url,{...opt,credentials:'same-origin',headers:{...hdr(),...(opt.headers||{})}});if(r.status===401){document.getElementById('app').classList.add('app-hidden');document.getElementById('login').style.display='block'}if(!r.ok)throw new Error((await r.text())||r.status);return r}
async function loadPayments(){try{const rows=await (await api('/v1/admin/payments?status=pending')).json();const root=document.getElementById('payments');root.innerHTML=rows.length?'':'<div class="muted">درخواستی در انتظار نیست.</div>';for(const p of rows){const d=document.createElement('div');d.className='payment';d.innerHTML=`<div class="row"><b>#${p.id}</b><span class="badge">${p.kind}</span><span>${Number(p.amount_toman).toLocaleString()} تومان</span><span class="muted">${p.email}</span></div><div class="small muted">پلن: ${p.plan_code||'-'} • قلب تخفیف: ${p.requested_hearts||0}</div><div class="row" style="margin-top:9px"><button class="ghost" onclick="showReceipt(${p.id},this)">رسید</button><button class="primary" onclick="review(${p.id},'approved')">تأیید</button><button class="danger" onclick="review(${p.id},'rejected')">رد</button></div><div id="receipt-${p.id}"></div>`;root.appendChild(d)}}catch(e){document.getElementById('payments').textContent='خطا: '+e.message}}
async function showReceipt(id,btn){try{const r=await fetch(`/v1/admin/payments/${id}/receipt`,{credentials:'same-origin'});if(!r.ok)throw new Error(await r.text());const b=await r.blob();const url=URL.createObjectURL(b);const root=document.getElementById('receipt-'+id);if(b.type==='application/pdf'){root.innerHTML=`<a href="${url}" target="_blank">باز کردن PDF رسید</a>`}else{root.innerHTML=`<img class="receipt" src="${url}">`}}catch(e){toast('رسید باز نشد')}}
async function review(id,status){const note=prompt(status==='approved'?'یادداشت تأیید (اختیاری)':'دلیل رد (اختیاری)')||'';try{await api(`/v1/admin/payments/${id}/review`,{method:'POST',body:JSON.stringify({status,admin_note:note||null})});toast('ثبت شد');loadPayments()}catch(e){toast('خطا: '+e.message)}}
async function loadSettings(){try{const s=await (await api('/v1/admin/settings')).json();for(const k of ['ad_reward_minutes','free_speed_mbps','tapsell_rewarded_zone_id','manual_card_number','manual_card_holder','android_store_url']){document.getElementById(k).value=s[k]??''}const once=s.one_time_missions||{};document.getElementById('instagram_url').value=once.instagram_follow?.url||'';document.getElementById('telegram_url').value=once.telegram_join?.url||''}catch(e){toast('تنظیمات خوانده نشد')}}
async function put(k,v){await api('/v1/admin/settings/'+encodeURIComponent(k),{method:'PUT',body:JSON.stringify(v)})}
async function saveSettings(){try{await put('ad_reward_minutes',Number(document.getElementById('ad_reward_minutes').value));await put('free_speed_mbps',Number(document.getElementById('free_speed_mbps').value));await put('tapsell_rewarded_zone_id',document.getElementById('tapsell_rewarded_zone_id').value.trim());await put('manual_card_number',document.getElementById('manual_card_number').value.trim());await put('manual_card_holder',document.getElementById('manual_card_holder').value.trim());await put('android_store_url',document.getElementById('android_store_url').value.trim());toast('ذخیره شد')}catch(e){toast('خطا: '+e.message)}}
async function saveSocial(){const instagram=document.getElementById('instagram_url').value.trim(),telegram=document.getElementById('telegram_url').value.trim();const payload={instagram_follow:{title:'دنبال‌کردن اینستاگرام Velo',url:instagram,hearts:10},telegram_join:{title:'عضویت در تلگرام Velo',url:telegram,hearts:10}};try{await put('one_time_missions',payload);toast('ذخیره شد')}catch(e){toast('خطا: '+e.message)}}
async function loadServers(){try{const rows=await (await api('/v1/admin/servers')).json();const root=document.getElementById('servers');root.innerHTML=rows.length?'':'—';for(const s of rows){const d=document.createElement('div');d.className='server';const hs=s.health_state||'unknown';d.innerHTML=`<div class="row"><b>${s.name}</b><span class="badge">${s.country_code} • ${s.tier}</span><span class="muted">${s.endpoint}</span><span>${s.agent_configured?'Node Agent':'Local'}</span><span>${s.active?'فعال':'خاموش'}</span><span class="badge">${hs}${s.health_failures?` • خطا ${s.health_failures}`:''}</span><button class="ghost" onclick="healthServer(${s.id})">Health</button><button class="ghost" onclick="reconcileServer(${s.id})">Reconcile</button><button class="ghost" onclick="toggleServer(${s.id})">${s.active?'خاموش':'روشن'}</button></div>`;root.appendChild(d)}}catch(e){root.textContent='خطا'}}
async function healthServer(id){try{const j=await (await api(`/v1/admin/servers/${id}/health`,{method:'POST'})).json();toast(j.ok?'سرور سالم است':'سرور مشکل دارد');loadServers()}catch(e){toast('Health ناموفق: '+e.message);loadServers()}}
async function reconcileServer(id){try{const j=await (await api(`/v1/admin/servers/${id}/reconcile`,{method:'POST'})).json();toast(`پاکسازی: ${j.removed_orphans||0} • نیاز به اتصال مجدد: ${j.missing_sessions||0}`)}catch(e){toast('Reconcile ناموفق: '+e.message)}}
async function toggleServer(id){try{await api(`/v1/admin/servers/${id}/toggle`,{method:'POST'});loadServers()}catch(e){toast('خطا')}}
function loadAll(){loadPayments();loadSettings();loadServers()}
async function resume(){try{await api('/v1/admin/settings');document.getElementById('login').style.display='none';document.getElementById('app').classList.remove('app-hidden');loadAll()}catch(e){}} resume();
</script></body></html>'''


class AdminLoginIn(BaseModel):
    password: str = Field(min_length=8, max_length=512)


@router.post('/admin/login')
def admin_login(payload: AdminLoginIn):
    expected = settings.admin_panel_password or settings.admin_api_key
    if not expected or not secrets.compare_digest(payload.password, expected):
        raise HTTPException(401, 'invalid_admin_credentials')
    response = JSONResponse({'ok': True})
    response.set_cookie(
        'velo_admin_session',
        admin_session_token(),
        max_age=max(1, settings.admin_session_hours) * 3600,
        httponly=True,
        secure=settings.environment.lower() == 'production',
        samesite='strict',
        path='/',
    )
    return response


@router.post('/admin/logout')
def admin_logout():
    response = JSONResponse({'ok': True})
    response.delete_cookie('velo_admin_session', path='/')
    return response


@router.get('/admin', response_class=HTMLResponse)
def admin_page():
    return HTML
