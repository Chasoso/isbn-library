import { type ReactNode, useEffect, useState } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { handleSignInCallback, signIn, signOut, userManager } from "./lib/auth";
import type { AuthState } from "./types";
import { FloatingScanButton } from "./view-helpers";

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
          <h1>蔵書ダッシュボードへログイン</h1>
          <p className="auth-copy">
            このアプリは認証済みユーザーのみ利用できます。管理者が作成した
            Cognito ユーザーでログインしてください。
          </p>
          <button className="primary-pill" onClick={() => void signIn()}>
            ログイン
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
  const hideFab = location.pathname === "/scan";

  return (
    <div className="app-shell">
      <div className="ambient ambient-left" aria-hidden="true" />
      <div className="ambient ambient-right" aria-hidden="true" />
      <header className="app-header">
        <div className="brand-block">
          <p className="kicker">ISBN DUPLICATE CHECK</p>
          <h1>{title}</h1>
          {subtitle ? <p className="subtle">{subtitle}</p> : null}
        </div>
        <nav className="nav-tabs" aria-label="メインメニュー">
          <NavLink to="/">ホーム</NavLink>
          <NavLink to="/books">蔵書一覧</NavLink>
          <NavLink to="/categories">カテゴリ管理</NavLink>
          <button className="ghost-link" onClick={() => void signOut()}>
            ログアウト
          </button>
        </nav>
      </header>
      <main className="page-content">{children}</main>
      {!hideFab ? <FloatingScanButton /> : null}
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
        setError("ログインコールバックの処理に失敗しました。");
      }
    };

    void complete();
  }, [navigate, onLoaded]);

  return (
    <div className="app-shell loading-screen">
      <div className="loading-panel">
        <p className="kicker">COGNITO CALLBACK</p>
        <h1>ログインを完了しています</h1>
        <p className="subtle">{error ?? "認証情報を確認しています。少しだけお待ちください。"}</p>
      </div>
    </div>
  );
}
