import { BrandMark } from "../../shared/ui/BrandMark";
import { ThemeToggle } from "../../shared/ui/ThemeToggle";
import { useAuth } from "../auth/useAuth";

export function DashboardPage() {
  const { user, logout } = useAuth();

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-row">
          <BrandMark compact />
          <div>
            <strong>Velo</strong>
            <span>پنل کاربری</span>
          </div>
        </div>
        <ThemeToggle />
      </header>

      <section className="dashboard-grid">
        <article className="hero-card">
          <span className="eyebrow">مرحله ۱</span>
          <h1>حساب شما آماده است</h1>
          <p>
            پایه وب Velo فعال شده است. در مرحله بعد، کانفیگ اختصاصی WireGuard و ۱۵ دقیقه هدیه شروع به همین حساب متصل می‌شود.
          </p>
          <div className="status-chip">
            <span className="status-dot" />
            ورود امن فعال
          </div>
        </article>

        <article className="panel-card">
          <span className="panel-label">حساب</span>
          <strong dir="ltr">{user?.email}</strong>
          <p>ورود با ایمیل و کد یک‌بارمصرف</p>
          <button className="secondary-button" type="button" onClick={() => void logout()}>
            خروج از حساب
          </button>
        </article>

        <article className="panel-card muted-card">
          <span className="panel-label">دسترسی VPN</span>
          <strong>در مرحله بعد</strong>
          <p>QR، فایل WireGuard، اعتبار رایگان و انتخاب Node بعد از تکمیل هسته دسترسی اضافه می‌شوند.</p>
        </article>
      </section>
    </main>
  );
}
