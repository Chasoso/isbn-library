import { type ReactNode, useEffect, useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { handleSignInCallback, signIn, signOut, userManager } from "./lib/auth";
import type { AuthState } from "./types";

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
          <h1>Sign in to your shelf</h1>
          <p className="auth-copy">
            This app is available to authenticated users only. Sign in with
            Cognito to continue.
          </p>
          <button className="primary-button full" onClick={() => void signIn()}>
            Sign in
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
  const [accountLabel, setAccountLabel] = useState("Menu");
  const [accountDetail, setAccountDetail] = useState<string | null>(null);
  const [accountInitials, setAccountInitials] = useState("U");

  useEffect(() => {
    let mounted = true;

    const loadUser = async (): Promise<void> => {
      const user = await userManager.getUser();
      if (!mounted) {
        return;
      }

      const name = user?.profile.name?.toString().trim() ?? "";
      const email = user?.profile.email?.toString().trim() ?? "";
      const label = name || email || "Menu";
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
        <div className="brand-block">
          <Link to="/" className="brand-wordmark" aria-label="ISBN Library home">
            ISBN LIBRARY
          </Link>
          <div className="brand-copy">
            <p className="kicker">EDITED SHELF</p>
            <h1>{title}</h1>
            {subtitle ? <p className="subtle">{subtitle}</p> : null}
          </div>
        </div>

        <div className="header-actions">
          <nav className="nav-tabs desktop-nav" aria-label="Main navigation">
            <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
              Home
            </NavLink>
            <NavLink to="/books" className={({ isActive }) => (isActive ? "active" : "")}>
              Books
            </NavLink>
            <NavLink to="/categories" className={({ isActive }) => (isActive ? "active" : "")}>
              Categories
            </NavLink>
          </nav>
          <button
            className="user-menu-trigger"
            type="button"
            onClick={() => setMenuOpen(true)}
            aria-haspopup="dialog"
            aria-expanded={menuOpen}
            aria-controls="account-menu"
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
      </header>

      <main className="page-content">{children}</main>

      <nav className="bottom-nav" aria-label="Mobile navigation">
        <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
          Home
        </NavLink>
        <NavLink to="/books" className={({ isActive }) => (isActive ? "active" : "")}>
          Books
        </NavLink>
        <NavLink
          to="/scan"
          className={({ isActive }) => (isActive ? "active bottom-nav-scan" : "bottom-nav-scan")}
        >
          Scan
        </NavLink>
        <NavLink to="/categories" className={({ isActive }) => (isActive ? "active" : "")}>
          Categories
        </NavLink>
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
                <h2 id="account-menu-title">User menu</h2>
              </div>
              <button
                type="button"
                className="icon-button"
                onClick={() => setMenuOpen(false)}
                aria-label="Close account menu"
              >
                ×
              </button>
            </div>
            <div className="menu-meta">
              <strong>{accountLabel}</strong>
              {accountDetail ? <p>{accountDetail}</p> : null}
            </div>
            <button type="button" className="primary-button full" onClick={() => void signOut()}>
              Logout
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
        setError("Sign-in callback failed.");
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
        <h1>Checking your sign-in</h1>
        <p className="subtle">{error ?? "Please wait while we complete authentication."}</p>
      </div>
    </div>
  );
}
