import { BrandMark } from "../../shared/ui/BrandMark";
import { ThemeToggle } from "../../shared/ui/ThemeToggle";
import { useAuth } from "../auth/useAuth";
import { VpnAccessPanel } from "../vpn/VpnAccessPanel";

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
          <span className="eyebrow">Velo Web</span>
          <h1>کانفیگ شخصی، بدون نصب اپ Velo</h1>
          <p>
            کانفیگ اختصاصی WireGuard را از همین پنل می‌گیری. در نسخه فعلی هر حساب فقط یک کانفیگ فعال دارد و ساخت کانفیگ جدید، قبلی را باطل می‌کند.
          </p>
          <div className="status-chip">
            <span className="status-dot" />
            حساب امن و آماده
          </div>
        </article>

        <VpnAccessPanel />

        <article className="panel-card">
          <span className="panel-label">حساب</span>
          <strong dir="ltr">{user?.email}</strong>
          <p>ورود با ایمیل و کد یک‌بارمصرف</p>
          <button className="secondary-button" type="button" onClick={() => void logout()}>
            خروج از حساب
          </button>
        </article>

        <article className="panel-card muted-card">
          <span className="panel-label">مرحله بعد</span>
          <strong>شارژ رایگان با تبلیغ</strong>
          <p>
            بعد از نهایی‌شدن صدور کانفیگ و تست روی Node خارجی، اعتبار تبلیغاتی و Premium به همین دسترسی اضافه می‌شوند.
          </p>
        </article>
      </section>
    </main>
  );
}
