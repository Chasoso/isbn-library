import { type ReactNode, useEffect, useMemo, useState } from "react";
import { Link, matchPath, useLocation, useNavigate } from "react-router-dom";
import { handleSignInCallback, signIn, signOut, userManager } from "./lib/auth";
import type { AuthState } from "./types";

type NavSection = "home" | "books" | "scan" | "categories";

function getActiveSection(pathname: string): NavSection {
  if (matchPath("/books", pathname) || matchPath("/books/*", pathname) || matchPath("/result/*", pathname)) {
    return "books";
  }

  if (matchPath("/scan", pathname)) {
    return "scan";
  }

  if (matchPath("/categories/*", pathname) || matchPath("/categories", pathname)) {
    return "categories";
  }

  return "home";
}

function ShellNavItem({
  to,
  label,
  active,
  mobile = false,
}: {
  to: string;
  label: string;
  active: boolean;
  mobile?: boolean;
}) {
  return (
    <Link
      to={to}
      className={[mobile ? "bottom-nav-item" : "nav-tab", active ? "active" : ""].filter(Boolean).join(" ")}
      aria-current={active ? "page" : undefined}
    >
      {label}
    </Link>
  );
}

export function ProtectedLayout({
  authState,
  children,
}: {
  authState: AuthState;
  children: ReactNode;
}) {
  if (!authState.isAuthenticated) {
    return (
      <div className="app-shell auth-screen">
        <div className="auth-card">
          <p className="kicker">ISBN LIBRARY</p>
          <h1>サインインして蔵書を開く</h1>
          <p className="auth-copy">
            Cognito でサインインすると、蔵書の確認、登録、検索、編集を行えます。
          </p>
          <button className="primary-button full" onClick={() => void signIn()}>
            サインイン
          </button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

export function AppLayout({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string | null;
  children: ReactNode;
}) {
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const [accountLabel, setAccountLabel] = useState("アカウント");
  const [accountDetail, setAccountDetail] = useState<string | null>(null);
  const [accountInitials, setAccountInitials] = useState("U");

  const activeSection = useMemo(() => getActiveSection(location.pathname), [location.pathname]);

  useEffect(() => {
    let mounted = true;

    const loadUser = async (): Promise<void> => {
      const user = await userManager.getUser();
      if (!mounted) {
        return;
      }

      const name = user?.profile.name?.toString().trim() ?? "";
      const email = user?.profile.email?.toString().trim() ?? "";
      const label = name || email || "アカウント";
      const initials = label
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((part) => part[0]?.toUpperCase() ?? "")
        .join("")
        .slice(0, 2);

      setAccountLabel(label);
      setAccountDetail(email || name || null);
      setAccountInitials(initials || "U");
    };

    void loadUser();

    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  return (
    <div className="app-shell editorial-shell">
      <header className="app-header">
        <div className="header-topline">
          <Link to="/" className="brand-wordmark" aria-label="ISBN Library ホーム">
            <span className="brand-wordmark-main">ISBN LIBRARY</span>
            <span className="brand-wordmark-sub">EDITED SHELF</span>
          </Link>

          <nav className="nav-tabs desktop-nav" aria-label="メインナビゲーション">
            <ShellNavItem to="/" label="ホーム" active={activeSection === "home"} />
            <ShellNavItem to="/books" label="蔵書一覧" active={activeSection === "books"} />
            <ShellNavItem to="/categories" label="カテゴリ管理" active={activeSection === "categories"} />
          </nav>

          <button
            className="user-menu-trigger"
            type="button"
            onClick={() => setMenuOpen(true)}
            aria-haspopup="dialog"
            aria-expanded={menuOpen}
            aria-controls="account-menu"
            aria-label={`アカウント ${accountLabel}`}
          >
            <span className="user-avatar" aria-hidden="true">
              {accountInitials}
            </span>
            <span className="user-menu-copy">
              <small>ACCOUNT</small>
              <strong>{accountLabel}</strong>
            </span>
          </button>
        </div>

        <div className="header-copy">
          <h1>{title}</h1>
          {subtitle ? <p className="header-subtitle">{subtitle}</p> : null}
        </div>
      </header>

      <main className="page-content">{children}</main>

      <nav className="bottom-nav" aria-label="モバイルナビゲーション">
        <ShellNavItem to="/" label="ホーム" active={activeSection === "home"} mobile />
        <ShellNavItem to="/books" label="蔵書一覧" active={activeSection === "books"} mobile />
        <ShellNavItem to="/scan" label="スキャン" active={activeSection === "scan"} mobile />
        <ShellNavItem to="/categories" label="カテゴリ管理" active={activeSection === "categories"} mobile />
      </nav>

      {menuOpen ? (
        <div className="modal-backdrop shell-menu-backdrop" onMouseDown={() => setMenuOpen(false)}>
          <section
            id="account-menu"
            className="menu-sheet"
            role="dialog"
            aria-modal="true"
            aria-labelledby="account-menu-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="sheet-heading">
              <div>
                <p className="eyebrow">ACCOUNT</p>
                <h2 id="account-menu-title">アカウント</h2>
              </div>
              <button
                type="button"
                className="icon-button"
                onClick={() => setMenuOpen(false)}
                aria-label="アカウントメニューを閉じる"
              >
                ×
              </button>
            </div>
            <div className="menu-meta">
              <strong>{accountLabel}</strong>
              {accountDetail ? <p>{accountDetail}</p> : null}
            </div>
            <button type="button" className="primary-button full" onClick={() => void signOut()}>
              ログアウト
            </button>
          </section>
        </div>
      ) : null}
    </div>
  );
}

export function AuthCallbackPage({
  onLoaded,
}: {
  onLoaded: (state: AuthState) => void;
}) {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const complete = async (): Promise<void> => {
      try {
        await handleSignInCallback();
        const user = await userManager.getUser();
        onLoaded({
          isAuthenticated: Boolean(user && !user.expired),
          accessToken: user?.access_token ?? null,
          email: user?.profile.email?.toString() ?? null,
          name: user?.profile.name?.toString() ?? null,
          loading: false,
        });
        navigate("/", { replace: true });
      } catch {
        setError("サインインの処理に失敗しました。");
      }
    };

    void complete();
  }, [navigate, onLoaded]);

  useEffect(() => {
    if (!error) {
      return;
    }

    const timer = window.setTimeout(() => {
      window.location.replace("/");
    }, 2400);

    return () => window.clearTimeout(timer);
  }, [error]);

  return (
    <div className="app-shell loading-screen">
      <div className="loading-panel">
        <p className="kicker">COGNITO CALLBACK</p>
        <h1>{error ? "サインインできませんでした" : "サインインを完了しています"}</h1>
        <p className="auth-copy">
          {error
            ? error
            : "認証結果を受け取って、蔵書画面へ戻っています。"}
        </p>
      </div>
    </div>
  );
}
