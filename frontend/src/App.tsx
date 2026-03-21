import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AuthCallbackPage, ProtectedLayout } from "./app-shell";
import { BookDetailPage } from "./pages/BookDetailPage";
import { BooksPage } from "./pages/BooksPage";
import { CategoriesPage } from "./pages/CategoriesPage";
import { HomePage } from "./pages/HomePage";
import { ResultPage } from "./pages/ResultPage";
import { ScanPage } from "./pages/ScanPage";
import { userManager } from "./lib/auth";
import type { AuthState } from "./types";

const initialAuthState: AuthState = {
  isAuthenticated: false,
  accessToken: null,
  email: null,
  name: null,
  loading: true,
};

function App() {
  const [authState, setAuthState] = useState<AuthState>(initialAuthState);

  useEffect(() => {
    let mounted = true;

    const loadUser = async (): Promise<void> => {
      const user = await userManager.getUser();
      if (!mounted) {
        return;
      }

      setAuthState({
        isAuthenticated: Boolean(user && !user.expired),
        accessToken: user?.access_token ?? null,
        email: user?.profile.email?.toString() ?? null,
        name: user?.profile.name?.toString() ?? null,
        loading: false,
      });
    };

    void loadUser();
    return () => {
      mounted = false;
    };
  }, []);

  if (authState.loading) {
    return (
      <div className="app-shell loading-screen">
        <div className="loading-panel">
          <p className="kicker">ISBN LIBRARY</p>
          <h1>本棚を読み込み中です</h1>
          <p className="subtle">認証状態を確認して、あなたの蔵書を開いています。</p>
        </div>
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/auth/callback" element={<AuthCallbackPage onLoaded={setAuthState} />} />
      <Route
        path="*"
        element={
          <ProtectedLayout authState={authState}>
            <Routes>
              <Route path="/" element={<HomePage authState={authState} />} />
              <Route path="/scan" element={<ScanPage />} />
              <Route
                path="/result/:isbn"
                element={<ResultPage accessToken={authState.accessToken ?? ""} />}
              />
              <Route path="/books" element={<BooksPage accessToken={authState.accessToken ?? ""} />} />
              <Route
                path="/books/:isbn"
                element={<BookDetailPage accessToken={authState.accessToken ?? ""} />}
              />
              <Route
                path="/categories"
                element={<CategoriesPage accessToken={authState.accessToken ?? ""} />}
              />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </ProtectedLayout>
        }
      />
    </Routes>
  );
}

export default App;
