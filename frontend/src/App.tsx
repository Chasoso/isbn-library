import { Html5Qrcode } from "html5-qrcode";
import { useEffect, useMemo, useState } from "react";
import {
  Link,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams,
} from "react-router-dom";
import { signIn, signOut, userManager, handleSignInCallback } from "./lib/auth";
import { ApiError, createBook, deleteBook, getBook, getBooks, lookupBook } from "./lib/api";
import { normalizeIsbn } from "./lib/isbn";
import type { AuthState, Book, BookLookupResult } from "./types";

const initialAuthState: AuthState = {
  isAuthenticated: false,
  accessToken: null,
  email: null,
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
      <div className="page-shell">
        <p>認証状態を確認しています...</p>
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
                element={<ResultPage accessToken={authState.accessToken!} />}
              />
              <Route path="/books" element={<BooksPage accessToken={authState.accessToken!} />} />
              <Route
                path="/books/:isbn"
                element={<BookDetailPage accessToken={authState.accessToken!} />}
              />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </ProtectedLayout>
        }
      />
    </Routes>
  );
}

function ProtectedLayout({
  authState,
  children,
}: {
  authState: AuthState;
  children: JSX.Element;
}) {
  const location = useLocation();

  if (!authState.isAuthenticated) {
    return (
      <div className="page-shell centered">
        <div className="card">
          <h1>ISBN Library</h1>
          <p>このアプリは認証済みユーザーのみ利用できます。</p>
          <p className="muted">
            自己サインアップは無効です。管理者が作成した Cognito ユーザーでログインしてください。
          </p>
          <button className="primary-button" onClick={() => void signIn()}>
            Cognito でログイン
          </button>
          <p className="muted">現在のパス: {location.pathname}</p>
        </div>
      </div>
    );
  }

  return children;
}

function Layout({
  title,
  email,
  children,
}: {
  title: string;
  email?: string | null;
  children: JSX.Element | JSX.Element[];
}) {
  return (
    <div className="page-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">ISBN DUPLICATE CHECK</p>
          <h1>{title}</h1>
          {email ? <p className="muted">{email}</p> : null}
        </div>
        <nav className="top-nav">
          <Link to="/">ホーム</Link>
          <Link to="/scan">スキャン</Link>
          <Link to="/books">蔵書一覧</Link>
          <button className="link-button" onClick={() => void signOut()}>
            ログアウト
          </button>
        </nav>
      </header>
      {children}
    </div>
  );
}

function AuthCallbackPage({
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
          loading: false,
        });
        navigate("/", { replace: true });
      } catch (_callbackError) {
        setError("ログインコールバックの処理に失敗しました。");
      }
    };

    void complete();
  }, [navigate, onLoaded]);

  return (
    <div className="page-shell centered">
      <div className="card">
        <h1>ログイン処理中</h1>
        <p>{error ?? "Cognito からの応答を処理しています..."}</p>
      </div>
    </div>
  );
}

function HomePage({ authState }: { authState: AuthState }) {
  const navigate = useNavigate();
  const [books, setBooks] = useState<Book[]>([]);
  const [searchText, setSearchText] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async (): Promise<void> => {
      try {
        const result = await getBooks(authState.accessToken!);
        setBooks(
          [...result.items].sort((a, b) => b.createdAt.localeCompare(a.createdAt)).slice(0, 5),
        );
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, [authState.accessToken]);

  return (
    <Layout title="ホーム" email={authState.email}>
      <main className="stack">
        <section className="hero-card">
          <p className="hero-label">重複購入をその場で防ぐ</p>
          <h2>ISBN を読み取って、登録済みか即判定</h2>
          <div className="hero-actions">
            <Link className="primary-button" to="/scan">
              スキャン開始
            </Link>
            <Link className="secondary-button" to="/books">
              蔵書一覧を見る
            </Link>
          </div>
        </section>

        <section className="card">
          <h3>タイトル検索</h3>
          <form
            className="search-row"
            onSubmit={(event) => {
              event.preventDefault();
              navigate(`/books?q=${encodeURIComponent(searchText.trim())}`);
            }}
          >
            <input
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
              placeholder="タイトルを入力"
            />
            <button className="primary-button" type="submit">
              検索
            </button>
          </form>
        </section>

        <section className="card">
          <h3>最近登録した本</h3>
          {loading ? <p>読み込み中...</p> : null}
          {!loading && books.length === 0 ? <p>まだ本が登録されていません。</p> : null}
          <div className="book-list">
            {books.map((book) => (
              <Link key={book.isbn} to={`/books/${book.isbn}`} className="book-row">
                {book.coverImageUrl ? (
                  <img src={book.coverImageUrl} alt={book.title} />
                ) : (
                  <div className="cover-placeholder">NO IMAGE</div>
                )}
                <div>
                  <strong>{book.title}</strong>
                  <p>{book.author || "著者不明"}</p>
                  <p className="muted">{book.isbn}</p>
                </div>
              </Link>
            ))}
          </div>
        </section>
      </main>
    </Layout>
  );
}

function ScanPage() {
  const navigate = useNavigate();
  const [message, setMessage] = useState("カメラを起動しています...");

  useEffect(() => {
    const elementId = "scanner";
    const scanner = new Html5Qrcode(elementId);
    let active = true;
    let detected = false;
    let started = false;

    const start = async (): Promise<void> => {
      try {
        await scanner.start(
          { facingMode: "environment" },
          { fps: 10, qrbox: { width: 250, height: 140 } },
          async (decodedText) => {
            if (detected) {
              return;
            }

            const isbn = normalizeIsbn(decodedText);

            if (!isbn) {
              setMessage("ISBN / EAN-13 を読み取ってください。");
              return;
            }

            detected = true;
            setMessage(`ISBN ${isbn} を検出しました。判定画面へ移動します...`);
            await scanner.stop();
            if (active) {
              navigate(`/result/${isbn}`);
            }
          },
          () => undefined,
        );
        started = true;
      } catch (_error) {
        setMessage("カメラを利用できません。ブラウザ権限を確認してください。");
      }
    };

    void start();

    return () => {
      active = false;
      if (started) {
        void scanner.stop().catch(() => undefined);
      }
      scanner.clear();
    };
  }, [navigate]);

  return (
    <Layout title="スキャン">
      <main className="stack">
        <section className="card">
          <p>{message}</p>
          <div id="scanner" className="scanner-box" />
        </section>
      </main>
    </Layout>
  );
}

function ResultPage({ accessToken }: { accessToken: string }) {
  const { isbn = "" } = useParams();
  const navigate = useNavigate();
  const [book, setBook] = useState<BookLookupResult | Book | null>(null);
  const [registered, setRegistered] = useState(false);
  const [lookupFailed, setLookupFailed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const load = async (): Promise<void> => {
      setLoading(true);
      setLookupFailed(false);
      setMessage(null);

      try {
        const existing = await getBook(accessToken, isbn);
        setRegistered(true);
        setBook(existing);
      } catch (error) {
        if (!(error instanceof ApiError) || error.status !== 404) {
          setMessage("登録状況の確認に失敗しました。");
          setLoading(false);
          return;
        }

        setRegistered(false);

        try {
          const lookedUp = await lookupBook(accessToken, isbn);
          setBook(lookedUp);
        } catch (lookupError) {
          if (lookupError instanceof ApiError && lookupError.status === 404) {
            setLookupFailed(true);
            setBook(null);
          } else {
            setMessage("書誌情報の取得に失敗しました。");
          }
        }
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, [accessToken, isbn]);

  const statusText = useMemo(
    () => (registered ? "この本はすでに登録されています" : "この本は未登録です"),
    [registered],
  );

  const handleCreate = async (): Promise<void> => {
    if (!book || registered) {
      return;
    }

    try {
      await createBook(accessToken, {
        isbn,
        title: book.title,
        author: book.author,
        publisher: book.publisher,
        publishedDate: book.publishedDate,
        coverImageUrl: book.coverImageUrl,
      });
      setMessage("登録しました。");
      setRegistered(true);
      navigate(`/books/${isbn}`, { replace: true });
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setRegistered(true);
        setMessage("すでに登録済みでした。");
      } else {
        setMessage("登録に失敗しました。");
      }
    }
  };

  return (
    <Layout title="判定結果">
      <main className="stack">
        <section className={`card status-card ${registered ? "registered" : "unregistered"}`}>
          <p className="muted">ISBN: {isbn}</p>
          <h2>{loading ? "確認中..." : statusText}</h2>
          {message ? <p>{message}</p> : null}
        </section>

        <section className="card">
          <h3>書誌情報</h3>
          {loading ? <p>読み込み中...</p> : null}
          {!loading && lookupFailed ? (
            <p>Google Books API から書誌情報を取得できませんでした。</p>
          ) : null}
          {!loading && book ? (
            <div className="detail-grid">
              {book.coverImageUrl ? (
                <img className="detail-cover" src={book.coverImageUrl} alt={book.title} />
              ) : null}
              <div>
                <p>
                  <strong>タイトル:</strong> {book.title || "-"}
                </p>
                <p>
                  <strong>著者:</strong> {book.author || "-"}
                </p>
                <p>
                  <strong>出版社:</strong> {book.publisher || "-"}
                </p>
                <p>
                  <strong>出版日:</strong> {book.publishedDate || "-"}
                </p>
              </div>
            </div>
          ) : null}
          {!loading && !registered && book ? (
            <button className="primary-button" onClick={() => void handleCreate()}>
              この本を登録する
            </button>
          ) : null}
        </section>
      </main>
    </Layout>
  );
}

function BooksPage({ accessToken }: { accessToken: string }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchText, setSearchText] = useState("");
  const query = new URLSearchParams(location.search).get("q") ?? "";

  useEffect(() => {
    setSearchText(query);
  }, [query]);

  useEffect(() => {
    const load = async (): Promise<void> => {
      setLoading(true);
      try {
        const result = await getBooks(accessToken, query);
        setBooks(result.items);
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, [accessToken, query]);

  return (
    <Layout title="蔵書一覧">
      <main className="stack">
        <section className="card">
          <form
            className="search-row"
            onSubmit={(event) => {
              event.preventDefault();
              navigate(`/books?q=${encodeURIComponent(searchText.trim())}`);
            }}
          >
            <input
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
              placeholder="タイトルで検索"
            />
            <button className="primary-button" type="submit">
              検索
            </button>
          </form>
          <p className="muted">{query ? `検索条件: ${query}` : "全件表示"}</p>
          {loading ? <p>読み込み中...</p> : null}
          {!loading && books.length === 0 ? <p>該当する書籍はありません。</p> : null}
          <div className="book-list">
            {books.map((book) => (
              <Link key={book.isbn} className="book-row" to={`/books/${book.isbn}`}>
                {book.coverImageUrl ? (
                  <img src={book.coverImageUrl} alt={book.title} />
                ) : (
                  <div className="cover-placeholder">NO IMAGE</div>
                )}
                <div>
                  <strong>{book.title}</strong>
                  <p>{book.author || "著者不明"}</p>
                  <p className="muted">{book.isbn}</p>
                </div>
              </Link>
            ))}
          </div>
        </section>
      </main>
    </Layout>
  );
}

function BookDetailPage({ accessToken }: { accessToken: string }) {
  const { isbn = "" } = useParams();
  const navigate = useNavigate();
  const [book, setBook] = useState<Book | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const load = async (): Promise<void> => {
      try {
        const result = await getBook(accessToken, isbn);
        setBook(result);
      } catch (_error) {
        setMessage("書籍情報の取得に失敗しました。");
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, [accessToken, isbn]);

  const handleDelete = async (): Promise<void> => {
    if (!window.confirm("この書籍を削除しますか？")) {
      return;
    }

    try {
      await deleteBook(accessToken, isbn);
      navigate("/books", { replace: true });
    } catch (_error) {
      setMessage("削除に失敗しました。");
    }
  };

  return (
    <Layout title="書籍詳細">
      <main className="stack">
        <section className="card">
          {loading ? <p>読み込み中...</p> : null}
          {message ? <p>{message}</p> : null}
          {book ? (
            <div className="detail-grid">
              {book.coverImageUrl ? (
                <img className="detail-cover" src={book.coverImageUrl} alt={book.title} />
              ) : (
                <div className="cover-placeholder large">NO IMAGE</div>
              )}
              <div>
                <h2>{book.title}</h2>
                <p>
                  <strong>著者:</strong> {book.author || "-"}
                </p>
                <p>
                  <strong>出版社:</strong> {book.publisher || "-"}
                </p>
                <p>
                  <strong>出版日:</strong> {book.publishedDate || "-"}
                </p>
                <p>
                  <strong>ISBN:</strong> {book.isbn}
                </p>
                <p>
                  <strong>登録日時:</strong> {book.createdAt}
                </p>
              </div>
            </div>
          ) : null}
          {book ? (
            <button className="danger-button" onClick={() => void handleDelete()}>
              削除する
            </button>
          ) : null}
        </section>
      </main>
    </Layout>
  );
}

export default App;
