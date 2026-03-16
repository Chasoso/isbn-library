import { BrowserMultiFormatReader } from "@zxing/browser";
import {
  BarcodeFormat,
  DecodeHintType,
  NotFoundException,
  ChecksumException,
  FormatException,
} from "@zxing/library";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  Link,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams,
} from "react-router-dom";
import { categories, type BookFormat, bookFormats, type Category } from "./catalog";
import { signIn, signOut, userManager, handleSignInCallback } from "./lib/auth";
import { ApiError, createBook, deleteBook, getBook, getBooks, lookupBook } from "./lib/api";
import { normalizeIsbn } from "./lib/isbn";
import type { AuthState, Book, BookLookupResult } from "./types";

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
            ログイン
          </button>
        </div>
      </div>
    );
  }

  return children;
}

function Layout({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string | null;
  children: JSX.Element | JSX.Element[];
}) {
  return (
    <div className="page-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">ISBN DUPLICATE CHECK</p>
          <h1>{title}</h1>
          {subtitle ? <p className="muted">{subtitle}</p> : null}
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
    <Layout title="ホーム" subtitle={authState.name}>
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
                  <p className="muted">
                    {book.bookFormat} / {book.category}
                  </p>
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
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const controlsRef = useRef<{ stop: () => void } | null>(null);
  const [message, setMessage] = useState(
    "カメラを準備しています。バーコードを枠いっぱいに映してください。",
  );

  useEffect(() => {
    const hints = new Map();
    hints.set(DecodeHintType.POSSIBLE_FORMATS, [
      BarcodeFormat.EAN_13,
      BarcodeFormat.EAN_8,
      BarcodeFormat.UPC_A,
      BarcodeFormat.UPC_E,
    ]);
    hints.set(DecodeHintType.TRY_HARDER, true);

    const reader = new BrowserMultiFormatReader(hints, {
      delayBetweenScanAttempts: 20,
      delayBetweenScanSuccess: 500,
    });

    let active = true;
    let detected = false;

    const onDetected = async (text: string): Promise<void> => {
      if (detected) {
        return;
      }

      const isbn = normalizeIsbn(text);
      if (!isbn) {
        setMessage("ISBN バーコードを枠内に水平に映してください。");
        return;
      }

      detected = true;
      controlsRef.current?.stop();
      setMessage(`ISBN ${isbn} を検出しました。判定画面へ移動します...`);
      if (active) {
        navigate(`/result/${isbn}`);
      }
    };

    const applyVideoTrackTuning = async (): Promise<void> => {
      const track = videoRef.current?.srcObject instanceof MediaStream
        ? videoRef.current.srcObject.getVideoTracks()[0]
        : null;

      if (!track) {
        return;
      }

      const capabilities = track.getCapabilities?.() as Record<string, unknown> | undefined;
      const advanced: Record<string, unknown> = {};

      const focusModes = capabilities?.focusMode as string[] | undefined;
      if (focusModes?.includes("continuous")) {
        advanced.focusMode = "continuous";
      }

      const exposureModes = capabilities?.exposureMode as string[] | undefined;
      if (exposureModes?.includes("continuous")) {
        advanced.exposureMode = "continuous";
      }

      const whiteBalanceModes = capabilities?.whiteBalanceMode as string[] | undefined;
      if (whiteBalanceModes?.includes("continuous")) {
        advanced.whiteBalanceMode = "continuous";
      }

      const zoom = capabilities?.zoom as { max?: number } | undefined;
      if (zoom?.max && zoom.max >= 2) {
        advanced.zoom = Math.min(2, zoom.max);
      }

      if (Object.keys(advanced).length > 0) {
        await track
          .applyConstraints({ advanced: [advanced as MediaTrackConstraintSet] })
          .catch(() => undefined);
      }
    };

    const start = async (): Promise<void> => {
      if (!videoRef.current) {
        setMessage("スキャン画面の初期化に失敗しました。");
        return;
      }

      try {
        const devices = await BrowserMultiFormatReader.listVideoInputDevices();
        const preferredDevice =
          devices.find((device) => /back|rear|environment|背面/i.test(device.label)) ??
          devices[0];

        if (!preferredDevice) {
          setMessage("利用可能なカメラが見つかりません。");
          return;
        }

        const controls = await reader.decodeFromConstraints(
          {
            audio: false,
            video: {
              deviceId: { exact: preferredDevice.deviceId },
              facingMode: "environment",
              width: { ideal: 1920 },
              height: { ideal: 1080 },
              aspectRatio: { ideal: 1.7777778 },
            },
          },
          videoRef.current,
          (result, error) => {
            if (result) {
              void onDetected(result.getText());
              return;
            }

            if (
              error &&
              !(
                error instanceof NotFoundException ||
                error instanceof ChecksumException ||
                error instanceof FormatException
              )
            ) {
              setMessage(`読み取りに失敗しました: ${error.message}`);
            }
          },
        );

        controlsRef.current = controls;
        await applyVideoTrackTuning();
        setMessage("バーコードを横向きのまま枠いっぱいに映し、少し離して固定してください。");
      } catch (error) {
        const detail = error instanceof Error ? error.message : String(error);

        if (/Permission|denied|NotAllowed/i.test(detail)) {
          setMessage("カメラ権限が拒否されています。ブラウザのカメラ許可を確認してください。");
          return;
        }

        if (/secure|https|origin/i.test(detail)) {
          setMessage("カメラは HTTPS または localhost でのみ利用できます。");
          return;
        }

        setMessage(`カメラを起動できませんでした: ${detail}`);
      }
    };

    void start();

    return () => {
      active = false;
      controlsRef.current?.stop();
      controlsRef.current = null;
    };
  }, [navigate]);

  return (
    <Layout title="スキャン">
      <main className="stack">
        <section className="card">
          <p>{message}</p>
          <ul className="hint-list">
            <li>ISBN バーコードを横向きのままガイド枠に合わせてください。</li>
            <li>近づけすぎるとピントが外れるので、少し離して固定すると読み取りやすいです。</li>
            <li>明るい場所で、影や反射が入らない角度にすると精度が上がります。</li>
          </ul>
          <div className="scanner-shell">
            <video ref={videoRef} className="scanner-video" muted playsInline autoPlay />
            <div className="scanner-overlay" aria-hidden="true">
              <div className="scanner-target" />
            </div>
          </div>
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
  const [bookFormat, setBookFormat] = useState<BookFormat>("その他");
  const [category, setCategory] = useState<Category>("その他");

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
          } else if (lookupError instanceof ApiError && lookupError.status === 503) {
            setMessage("書誌情報取得が混み合っています。少し待って再試行してください。");
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
        bookFormat,
        category,
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
                <p>
                  <strong>形態:</strong> {"bookFormat" in book ? book.bookFormat : bookFormat}
                </p>
                <p>
                  <strong>ジャンル:</strong> {"category" in book ? book.category : category}
                </p>
              </div>
            </div>
          ) : null}
          {!loading && !registered && book ? (
            <div className="classification-grid">
              <label>
                <span>形態</span>
                <select
                  value={bookFormat}
                  onChange={(event) => setBookFormat(event.target.value as BookFormat)}
                >
                  {bookFormats.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>ジャンル</span>
                <select
                  value={category}
                  onChange={(event) => setCategory(event.target.value as Category)}
                >
                  {categories.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </label>
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
  const [bookFormatFilter, setBookFormatFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const params = new URLSearchParams(location.search);
  const query = params.get("q") ?? "";
  const bookFormat = params.get("bookFormat") ?? "";
  const category = params.get("category") ?? "";

  useEffect(() => {
    setSearchText(query);
    setBookFormatFilter(bookFormat);
    setCategoryFilter(category);
  }, [query, bookFormat, category]);

  useEffect(() => {
    const load = async (): Promise<void> => {
      setLoading(true);
      try {
        const result = await getBooks(accessToken, {
          query,
          bookFormat,
          category,
        });
        setBooks(result.items);
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, [accessToken, query, bookFormat, category]);

  return (
    <Layout title="蔵書一覧">
      <main className="stack">
        <section className="card">
          <form
            className="search-row"
            onSubmit={(event) => {
              event.preventDefault();
              const nextParams = new URLSearchParams();
              if (searchText.trim()) {
                nextParams.set("q", searchText.trim());
              }
              if (bookFormatFilter) {
                nextParams.set("bookFormat", bookFormatFilter);
              }
              if (categoryFilter) {
                nextParams.set("category", categoryFilter);
              }
              navigate(`/books${nextParams.toString() ? `?${nextParams.toString()}` : ""}`);
            }}
          >
            <input
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
              placeholder="タイトルで検索"
            />
            <select
              value={bookFormatFilter}
              onChange={(event) => setBookFormatFilter(event.target.value)}
            >
              <option value="">すべての形態</option>
              {bookFormats.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
            <select
              value={categoryFilter}
              onChange={(event) => setCategoryFilter(event.target.value)}
            >
              <option value="">すべてのジャンル</option>
              {categories.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
            <button className="primary-button" type="submit">
              検索
            </button>
          </form>
          <p className="muted">
            {query || bookFormat || category
              ? `検索条件: ${query || "タイトル指定なし"} / ${bookFormat || "形態すべて"} / ${category || "ジャンルすべて"}`
              : "全件表示"}
          </p>
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
                  <p className="muted">
                    {book.bookFormat} / {book.category}
                  </p>
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
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    const load = async (): Promise<void> => {
      try {
        const result = await getBook(accessToken, isbn);
        setBook(result);
        setNotFound(false);
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) {
          setNotFound(true);
          setMessage("対象の書籍は登録されていません。");
        } else {
          setMessage("書籍情報の取得に失敗しました。");
        }
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
    } catch {
      setMessage("削除に失敗しました。");
    }
  };

  return (
    <Layout title="書籍詳細">
      <main className="stack">
        <section className="card">
          {loading ? <p>読み込み中...</p> : null}
          {message ? <p>{message}</p> : null}
          {notFound ? (
            <p>
              <Link to="/books">蔵書一覧へ戻る</Link>
            </p>
          ) : null}
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
                  <strong>形態:</strong> {book.bookFormat}
                </p>
                <p>
                  <strong>ジャンル:</strong> {book.category}
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
