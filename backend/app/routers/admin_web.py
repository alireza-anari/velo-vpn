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
<div class="top"><div><div class="brand">💜 Velo Admin</div><div class="muted">مدیریت ساده اشتراک‌ها، کاربران و سرورهای Velo</div></div><div class="row"><button class="ghost" onclick="logout()">خروج</button></div></div>
<div class="grid"><section class="card wide"><h2>وضعیت کلی</h2><div id="dashboard" class="row muted">در حال بارگذاری…</div></section><section class="card"><h2>فعال‌سازی اشتراک</h2><label class="small">ایمیل کاربر</label><input id="grant_email" type="email" placeholder="user@example.com"><label class="small">مدت</label><select id="grant_days"><option value="15">۱۵ روز</option><option value="30">۱ ماه</option><option value="90">۳ ماه</option><option value="180">۶ ماه</option></select><label class="small">یادداشت اختیاری</label><input id="grant_note" placeholder="مثلاً پرداخت کارت‌به‌کارت"><button class="primary" style="width:100%" onclick="grantSubscription()">فعال‌سازی</button><p class="muted">اگر ایمیل هنوز حساب نداشته باشد، حساب از همین‌جا ایجاد می‌شود.</p></section><section class="card"><h2>جستجوی کاربر</h2><div class="row"><input id="user_query" placeholder="ایمیل" style="flex:1"><button class="ghost" onclick="loadUsers()">جستجو</button></div><div id="users" class="muted">—</div></section><section class="card wide"><div class="row" style="justify-content:space-between"><h2>پرداخت‌های در انتظار</h2><button class="ghost" onclick="loadPayments()">بروزرسانی</button></div><div id="payments" class="muted">—</div></section><section class="card wide"><div class="row" style="justify-content:space-between"><h2>سرورها</h2><button class="ghost" onclick="loadServers()">بروزرسانی</button></div><div id="servers" class="muted">—</div></section><section class="card wide"><h2>افزودن VPS</h2><p class="muted">بعد از اجرای اسکریپت آماده‌سازی روی VPS جدید، مقادیر خروجی را اینجا وارد کنید. اپ کاربران نیازی به Build جدید ندارد.</p><div class="grid"><div><label class="small">نام</label><input id="srv_name" placeholder="DE-01"><label class="small">کشور</label><input id="srv_country" value="DE"><label class="small">شهر</label><input id="srv_city" placeholder="Frankfurt"><label class="small">Endpoint Host / IP</label><input id="srv_host" placeholder="203.0.113.10"></div><div><label class="small">Public Key</label><input id="srv_key"><label class="small">Client CIDR</label><input id="srv_cidr" placeholder="10.77.2.0/24"><label class="small">نوع Node</label><select id="srv_tier"><option value="free">Free + Premium</option><option value="premium">Premium only</option><option value="vip">VIP</option></select><label class="small">Node Agent URL</label><input id="srv_agent_url" placeholder="http://203.0.113.10:8787"><label class="small">Node Agent Token</label><input id="srv_agent_token"></div></div><button class="primary" onclick="addServer()">ثبت سرور</button></section><section class="card wide"><div class="row" style="justify-content:space-between"><h2>اتصال‌های فعال</h2><button class="ghost" onclick="loadSessions()">بروزرسانی</button></div><div id="sessions" class="muted">—</div></section></div></div></main><div id="toast" class="toast"></div>
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
async function loadServers(){try{const rows=await (await api('/v1/admin/servers')).json();const root=document.getElementById('servers');root.innerHTML=rows.length?'':'—';for(const s of rows){const d=document.createElement('div');d.className='server';const hs=s.health_state||'unknown';const used=s.utilization_percent||0;d.innerHTML='<div class="row"><b>'+s.name+'</b><span class="badge">'+s.country_code+' • '+s.tier+'</span><span class="muted">'+s.endpoint+'</span><span>'+s.active_sessions+'/'+s.max_sessions+' اتصال</span><span class="badge">'+used+'٪ ظرفیت</span><span class="badge">'+hs+'</span><button class="ghost" onclick="healthServer('+s.id+')">Health</button><button class="ghost" onclick="reconcileServer('+s.id+')">Reconcile</button><button class="ghost" onclick="toggleServer('+s.id+')">'+(s.active?'خاموش':'روشن')+'</button></div>';root.appendChild(d)}}catch(e){document.getElementById('servers').textContent='خطا: '+e.message}}
async function healthServer(id){try{const j=await (await api(`/v1/admin/servers/${id}/health`,{method:'POST'})).json();toast(j.ok?'سرور سالم است':'سرور مشکل دارد');loadServers()}catch(e){toast('Health ناموفق: '+e.message);loadServers()}}
async function reconcileServer(id){try{const j=await (await api(`/v1/admin/servers/${id}/reconcile`,{method:'POST'})).json();toast(`پاکسازی: ${j.removed_orphans||0} • نیاز به اتصال مجدد: ${j.missing_sessions||0}`)}catch(e){toast('Reconcile ناموفق: '+e.message)}}
async function toggleServer(id){try{await api(`/v1/admin/servers/${id}/toggle`,{method:'POST'});loadServers()}catch(e){toast('خطا')}}
async function loadDashboard(){try{const d=await (await api('/v1/admin/dashboard')).json();document.getElementById('dashboard').innerHTML='<span class="badge">کاربر '+d.users+'</span><span class="badge">اشتراک فعال '+d.active_subscriptions+'</span><span class="badge">اتصال فعال '+d.active_sessions+'</span><span class="badge">پرداخت در انتظار '+d.pending_payments+'</span><span class="badge">سرور '+d.active_servers+'/'+d.total_servers+'</span>'}catch(e){document.getElementById('dashboard').textContent='خطا در دریافت وضعیت'}}
async function grantSubscription(){const email=document.getElementById('grant_email').value.trim();const days=Number(document.getElementById('grant_days').value);const note=document.getElementById('grant_note').value.trim();if(!email){toast('ایمیل را وارد کنید');return}try{const j=await (await api('/v1/admin/subscriptions/grant',{method:'POST',body:JSON.stringify({email,days,note:note||null})})).json();toast('اشتراک فعال شد تا '+String(j.ends_at).slice(0,10));loadDashboard();loadUsers()}catch(e){toast('خطا: '+e.message)}}
async function loadUsers(){try{const q=document.getElementById('user_query').value.trim();const rows=await (await api('/v1/admin/users?q='+encodeURIComponent(q))).json();const root=document.getElementById('users');root.innerHTML=rows.length?'':'کاربری پیدا نشد.';for(const u of rows){const d=document.createElement('div');d.className='payment';const sub=u.subscription_active?('فعال تا '+String(u.subscription_ends_at).slice(0,10)):'بدون اشتراک';d.innerHTML='<div><b>'+u.email+'</b></div><div class="small muted">'+sub+' • دستگاه '+u.devices+' • اتصال فعال '+u.active_sessions+'</div><div class="row" style="margin-top:7px"><button class="ghost" onclick="quickGrant(\''+u.email+'\',30)">+۱ ماه</button><button class="ghost" onclick="quickGrant(\''+u.email+'\',90)">+۳ ماه</button><button class="danger" onclick="revokeSubscription('+u.id+')">لغو اشتراک</button></div>';root.appendChild(d)}}catch(e){document.getElementById('users').textContent='خطا: '+e.message}}
async function quickGrant(email,days){try{await api('/v1/admin/subscriptions/grant',{method:'POST',body:JSON.stringify({email,days,note:'quick grant'})});toast('اشتراک تمدید شد');loadUsers();loadDashboard()}catch(e){toast('خطا: '+e.message)}}
async function revokeSubscription(id){if(!confirm('اشتراک این کاربر لغو شود؟ اتصال فعال هم قطع می‌شود.'))return;try{await api('/v1/admin/users/'+id+'/subscription/revoke',{method:'POST'});toast('اشتراک لغو شد');loadUsers();loadDashboard()}catch(e){toast('خطا: '+e.message)}}
async function loadSessions(){try{const rows=await (await api('/v1/admin/sessions?status=active')).json();const root=document.getElementById('sessions');root.innerHTML=rows.length?'':'اتصال فعالی وجود ندارد.';for(const x of rows){const d=document.createElement('div');d.className='server';d.innerHTML='<div class="row"><b>#'+x.id+'</b><span>'+(x.email||'Guest')+'</span><span class="badge">'+x.server+'</span><span class="muted">'+x.client_ip+'</span><span>'+ (x.premium?'Premium':'Free') +'</span></div>';root.appendChild(d)}}catch(e){document.getElementById('sessions').textContent='خطا: '+e.message}}
async function addServer(){const body={name:document.getElementById('srv_name').value.trim(),country_code:document.getElementById('srv_country').value.trim().toUpperCase(),city:document.getElementById('srv_city').value.trim(),endpoint_host:document.getElementById('srv_host').value.trim(),endpoint_port:51820,public_key:document.getElementById('srv_key').value.trim(),dns:'1.1.1.1',client_cidr:document.getElementById('srv_cidr').value.trim(),tier:document.getElementById('srv_tier').value,is_active:true,is_default:false,max_sessions:200,agent_url:document.getElementById('srv_agent_url').value.trim()||null,agent_token:document.getElementById('srv_agent_token').value.trim()||null};try{await api('/v1/admin/servers',{method:'POST',body:JSON.stringify(body)});toast('سرور ثبت شد');loadServers();loadDashboard()}catch(e){toast('خطا: '+e.message)}}
function loadAll(){loadDashboard();loadPayments();loadUsers();loadServers();loadSessions()}
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
