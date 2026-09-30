import { useCallback, useEffect, useMemo, useState } from "react";
import QRCode from "qrcode";
import { ApiError, api } from "../../lib/api";
import type { IssuedVpnConfig, WebVpnAccess } from "./types";

function formatDuration(seconds: number) {
  const safe = Math.max(0, seconds);
  const hours = Math.floor(safe / 3600);
  const minutes = Math.floor((safe % 3600) / 60);
  const secs = safe % 60;

  if (hours > 0) {
    return `${hours.toString().padStart(2, "0")}:${minutes
      .toString()
      .padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  }

  return `${minutes.toString().padStart(2, "0")}:${secs
    .toString()
    .padStart(2, "0")}`;
}

function messageFor(error: unknown) {
  if (error instanceof ApiError) {
    if (error.detail === "no_server_capacity") {
      return "در حال حاضر سرور آماده‌ای برای ساخت کانفیگ وجود ندارد.";
    }
    if (error.detail === "configuration_already_issued") {
      return "برای این حساب قبلاً کانفیگ ساخته شده است.";
    }
  }
  return "عملیات انجام نشد. دوباره تلاش کنید.";
}

export function VpnAccessPanel() {
  const [access, setAccess] = useState<WebVpnAccess | null>(null);
  const [issued, setIssued] = useState<IssuedVpnConfig | null>(null);
  const [qrDataUrl, setQrDataUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());

  const refresh = useCallback(async () => {
    try {
      const status = await api<WebVpnAccess>("/v1/web-vpn/access");
      setAccess(status);
      setError(null);
    } catch (requestError) {
      setError(messageFor(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function makeQr() {
      if (!issued) {
        setQrDataUrl(null);
        return;
      }
      const dataUrl = await QRCode.toDataURL(issued.configuration, {
        errorCorrectionLevel: "M",
        margin: 2,
        width: 300,
      });
      if (!cancelled) {
        setQrDataUrl(dataUrl);
      }
    }

    void makeQr();
    return () => {
      cancelled = true;
    };
  }, [issued]);

  const remainingSeconds = useMemo(() => {
    if (!access?.access_until) {
      return 0;
    }
    return Math.max(0, Math.floor((new Date(access.access_until).getTime() - now) / 1000));
  }, [access?.access_until, now]);

  async function issue(replace: boolean) {
    if (
      replace &&
      !window.confirm(
        "کانفیگ قبلی فوراً غیرفعال می‌شود. کانفیگ جدید ساخته شود؟",
      )
    ) {
      return;
    }

    setBusy(true);
    setError(null);
    try {
      const result = await api<IssuedVpnConfig>(
        replace ? "/v1/web-vpn/regenerate" : "/v1/web-vpn/provision",
        { method: "POST" },
      );
      setIssued(result);
      setAccess(result.access);
    } catch (requestError) {
      setError(messageFor(requestError));
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  function downloadConfig() {
    if (!issued) {
      return;
    }

    const blob = new Blob([issued.configuration], {
      type: "text/plain;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = issued.filename;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  async function copyConfig() {
    if (!issued) {
      return;
    }
    try {
      await navigator.clipboard.writeText(issued.configuration);
    } catch {
      setError("مرورگر اجازه کپی مستقیم نداد؛ فایل کانفیگ را دانلود کنید.");
    }
  }

  if (loading) {
    return (
      <article className="panel-card vpn-card vpn-card--wide">
        <span className="panel-label">دسترسی VPN</span>
        <strong>در حال بررسی...</strong>
      </article>
    );
  }

  if (!access?.provisioned) {
    return (
      <article className="panel-card vpn-card vpn-card--wide">
        <div className="vpn-card__header">
          <div>
            <span className="panel-label">دسترسی VPN</span>
            <h2>کانفیگ اختصاصی Velo</h2>
          </div>
          <span className="vpn-badge">هدیه شروع</span>
        </div>

        <p>
          اولین کانفیگ شما فقط برای همین حساب ساخته می‌شود و
          {" "}
          <strong>{access?.welcome_minutes ?? 15} دقیقه</strong>
          {" "}
          اعتبار اولیه دارد.
        </p>
        <div className="notice-box">
          تایمر هدیه از لحظه ساخت کانفیگ شروع می‌شود. بهتر است WireGuard را قبل از ادامه روی دستگاه نصب کرده باشید.
        </div>
        <button
          className="primary-button vpn-action"
          type="button"
          disabled={busy}
          onClick={() => void issue(false)}
        >
          {busy ? "در حال ساخت..." : "ساخت کانفیگ و شروع اعتبار"}
        </button>
        {error ? <p className="form-error" role="alert">{error}</p> : null}
      </article>
    );
  }

  const serverLabel = access.server
    ? `${access.server.country_code.toUpperCase()} · ${access.server.city || access.server.name}`
    : "نامشخص";

  return (
    <article className="panel-card vpn-card vpn-card--wide">
      <div className="vpn-card__header">
        <div>
          <span className="panel-label">دسترسی VPN</span>
          <h2>{access.active ? "کانفیگ فعال" : "کانفیگ غیرفعال"}</h2>
        </div>
        <span className={access.active ? "vpn-badge vpn-badge--active" : "vpn-badge"}>
          {access.premium ? "Premium" : access.active ? "Free" : "بدون اعتبار"}
        </span>
      </div>

      <div className="vpn-status-grid">
        <div>
          <span>سرور</span>
          <strong dir="ltr">{serverLabel}</strong>
        </div>
        <div>
          <span>زمان باقی‌مانده</span>
          <strong dir="ltr">{access.premium ? "Premium" : formatDuration(remainingSeconds)}</strong>
        </div>
        <div>
          <span>نسخه کانفیگ</span>
          <strong dir="ltr">v{access.config_version ?? 1}</strong>
        </div>
      </div>

      {issued ? (
        <section className="config-delivery" aria-label="کانفیگ WireGuard">
          <div className="qr-wrap">
            {qrDataUrl ? (
              <img src={qrDataUrl} alt="QR کانفیگ WireGuard Velo" />
            ) : (
              <span>در حال ساخت QR...</span>
            )}
          </div>
          <div className="config-actions">
            <strong>کانفیگ آماده است</strong>
            <p>
              QR را داخل WireGuard اسکن کن یا فایل را دانلود کن. کلید خصوصی فقط در همین پاسخ مرورگر نمایش داده می‌شود.
            </p>
            <button className="primary-button" type="button" onClick={downloadConfig}>
              دانلود فایل .conf
            </button>
            <button className="secondary-button" type="button" onClick={() => void copyConfig()}>
              کپی کانفیگ
            </button>
          </div>
        </section>
      ) : (
        <div className="notice-box">
          برای امنیت، Private Key کانفیگ روی سرور ذخیره نمی‌شود. اگر فایل قبلی را در اختیار نداری، یک کانفیگ جدید بساز؛ کانفیگ قبلی همان لحظه غیرفعال می‌شود.
        </div>
      )}

      {!issued ? (
        <button
          className="secondary-button vpn-action"
          type="button"
          disabled={busy}
          onClick={() => void issue(true)}
        >
          {busy ? "در حال ساخت..." : "ساخت کانفیگ جدید"}
        </button>
      ) : null}

      {error ? <p className="form-error" role="alert">{error}</p> : null}
    </article>
  );
}
