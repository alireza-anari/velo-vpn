import { FormEvent, useState } from "react";
import { ApiError, api } from "../../lib/api";
import { BrandMark } from "../../shared/ui/BrandMark";
import { useAuth } from "./useAuth";

type Step = "email" | "code";

const ERROR_MESSAGES: Record<string, string> = {
  too_many_otp_requests: "تعداد درخواست‌ها زیاد است. چند دقیقه دیگر دوباره تلاش کنید.",
  email_unavailable: "ارسال ایمیل موقتاً در دسترس نیست.",
  invalid_code: "کد واردشده صحیح نیست یا منقضی شده است.",
};

function errorText(error: unknown) {
  if (error instanceof ApiError) {
    return ERROR_MESSAGES[error.detail] ?? "درخواست انجام نشد. دوباره تلاش کنید.";
  }
  return "ارتباط با سرور برقرار نشد.";
}

export function LoginPage() {
  const { refresh } = useAuth();
  const [step, setStep] = useState<Step>("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [devCode, setDevCode] = useState<string | null>(null);

  async function requestOtp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage(null);
    setDevCode(null);

    try {
      const result = await api<{ sent: boolean; dev_code?: string }>(
        "/v1/auth/request-otp",
        { method: "POST", json: { email: email.trim() } },
      );
      if (result.dev_code) {
        setDevCode(result.dev_code);
      }
      setStep("code");
    } catch (error) {
      setMessage(errorText(error));
    } finally {
      setBusy(false);
    }
  }

  async function verifyOtp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage(null);

    try {
      await api("/v1/auth/verify-otp", {
        method: "POST",
        json: { email: email.trim(), code: code.trim() },
      });
      await refresh();
    } catch (error) {
      setMessage(errorText(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-card" aria-labelledby="auth-title">
        <BrandMark />
        <div className="auth-copy">
          <span className="eyebrow">Velo Web</span>
          <h1 id="auth-title">{step === "email" ? "ورود یا ثبت‌نام" : "تأیید ایمیل"}</h1>
          <p>
            {step === "email"
              ? "ایمیلت را وارد کن. برای ورود یک کد یک‌بارمصرف می‌فرستیم."
              : `کد ۶ رقمی ارسال‌شده به ${email} را وارد کن.`}
          </p>
        </div>

        {step === "email" ? (
          <form className="auth-form" onSubmit={requestOtp}>
            <label htmlFor="email">ایمیل</label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              inputMode="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="name@example.com"
              dir="ltr"
            />
            <button className="primary-button" type="submit" disabled={busy}>
              {busy ? "در حال ارسال..." : "ارسال کد ورود"}
            </button>
          </form>
        ) : (
          <form className="auth-form" onSubmit={verifyOtp}>
            <label htmlFor="otp">کد ورود</label>
            <input
              id="otp"
              className="otp-input"
              type="text"
              autoComplete="one-time-code"
              inputMode="numeric"
              pattern="[0-9]{6}"
              maxLength={6}
              required
              value={code}
              onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))}
              placeholder="••••••"
              dir="ltr"
            />
            <button className="primary-button" type="submit" disabled={busy}>
              {busy ? "در حال بررسی..." : "ورود به Velo"}
            </button>
            <button
              className="text-button"
              type="button"
              onClick={() => {
                setStep("email");
                setCode("");
                setMessage(null);
              }}
            >
              تغییر ایمیل
            </button>
          </form>
        )}

        {devCode ? (
          <p className="dev-note">Development OTP: <strong dir="ltr">{devCode}</strong></p>
        ) : null}
        {message ? <p className="form-error" role="alert">{message}</p> : null}

        <p className="security-note">
          نشست وب در Cookie امن HttpOnly نگهداری می‌شود و توکن ورود داخل Local Storage ذخیره نمی‌شود.
        </p>
      </section>
    </main>
  );
}
