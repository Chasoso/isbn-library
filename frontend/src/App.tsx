import { BrowserMultiFormatReader } from "@zxing/browser";
import {
  BarcodeFormat,
  ChecksumException,
  DecodeHintType,
  FormatException,
  NotFoundException,
} from "@zxing/library";
import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  Link,
  NavLink,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams,
} from "react-router-dom";
import { bookFormats, categories, type BookFormat, type Category } from "./catalog";
import { CoverFlowShelf } from "./components/CoverFlowShelf";
import { handleSignInCallback, signIn, signOut, userManager } from "./lib/auth";
import {
  ApiError,
  createBook,
  deleteBook,
  getBook,
  getBooks,
  lookupBook,
  updateBookStatus,
} from "./lib/api";
import { normalizeIsbn } from "./lib/isbn";
import { readingStatuses, type ReadingStatus } from "./readingStatus";
import type { AuthState, Book, BookLookupResult } from "./types";

const initialAuthState: AuthState = {
  isAuthenticated: false,
  accessToken: null,
  email: null,
  name: null,
  loading: true,
};
/*

const defaultBookFormat: BookFormat = "その他";
const defaultCategory: Category = "その他";

*/
const defaultBookFormat: BookFormat = bookFormats[bookFormats.length - 1];
const defaultCategory: Category = categories[categories.length - 1];
const defaultReadingStatus: ReadingStatus = readingStatuses[0];

const sortOptions = [
  { value: "newest", label: "登録日が新しい順" },
  { value: "oldest", label: "登録日が古い順" },
  { value: "title", label: "タイトル順" },
  { value: "author", label: "著者順" },
] as const;

type SortOption = (typeof sortOptions)[number]["value"];

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
          <h1>蔵書を準備しています</h1>
          <p className="subtle">認証状態を確認して、あなたの本棚を開いています。</p>
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
  children: ReactNode;
}) {
  if (!authState.isAuthenticated) {
    return (
      <div className="app-shell auth-screen">
        <div className="auth-card">
          <p className="kicker">ISBN LIBRARY</p>
          <h1>蔵書ダッシュボードへログイン</h1>
          <p className="auth-copy">
            このアプリは認証済みユーザーのみ利用できます。管理者が作成したアカウントでログインしてください。
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

function AppLayout({
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
    <div className="app-shell loading-screen">
      <div className="loading-panel">
        <p className="kicker">COGNITO CALLBACK</p>
        <h1>ログインを完了しています</h1>
        <p className="subtle">{error ?? "認証情報を確認しています。少しだけお待ちください。"}</p>
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
        const result = await getBooks(authState.accessToken ?? "");
        setBooks(sortBooks(result.items, "newest"));
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, [authState.accessToken]);

  const recentBooks = books.slice(0, 6);
  const monthlyCount = books.filter((book) => isInCurrentMonth(book.createdAt)).length;
  const lastAdded = books[0]?.createdAt ?? null;
  const categoryCount = new Set(books.map((book) => book.category)).size;

  return (
    <AppLayout title="ホーム" subtitle={authState.name ? `${authState.name}さんの蔵書ダッシュボード` : null}>
      <section className="dashboard-hero panel">
        <div className="hero-copy">
          <p className="section-label">あなたの蔵書</p>
          <h2>本棚の状態をひと目で把握</h2>
          <p className="subtle">
            重複購入の確認だけでなく、最近追加した本や分類の広がりまで、今の蔵書を気持ちよく眺められるホームです。
          </p>
        </div>
        <SummaryCards
          items={[
            {
              label: "総冊数",
              value: `${books.length}`,
              tone: "teal",
              caption: books.length > 0 ? "蔵書を管理中" : "最初の1冊を登録",
            },
            {
              label: "今月の追加",
              value: `+${monthlyCount}`,
              tone: "sky",
              caption: monthlyCount > 0 ? "今月の登録数" : "追加はまだありません",
            },
            {
              label: "最終登録",
              value: lastAdded ? formatRelativeTime(lastAdded) : "未登録",
              tone: "amber",
              caption: lastAdded ? formatDateTime(lastAdded) : `${categoryCount}カテゴリ`,
            },
          ]}
        />
      </section>

      <section className="panel search-panel">
        <div className="section-heading">
          <div>
            <p className="section-label">検索</p>
            <h3>次に読みたい1冊をすぐ探す</h3>
          </div>
        </div>
        <SearchBar
          value={searchText}
          onChange={setSearchText}
          placeholder="タイトル・著者で検索"
          submitLabel="検索"
          onSubmit={() => {
            const nextQuery = searchText.trim();
            navigate(`/books${nextQuery ? `?q=${encodeURIComponent(nextQuery)}` : ""}`);
          }}
        />
      </section>

      <section className="panel">
        <div className="section-heading">
          <div>
            <p className="section-label">最近追加した本</p>
            <h3>新しく棚に並んだ本</h3>
          </div>
          <Link className="text-link" to="/books">
            蔵書一覧を見る
          </Link>
        </div>
        {loading ? <p className="empty-copy">蔵書を読み込んでいます...</p> : null}
        {!loading && recentBooks.length === 0 ? (
          <div className="empty-state">
            <p>まだ本が登録されていません。</p>
            <p className="subtle">右下の「スキャンする」から、最初の1冊を登録できます。</p>
          </div>
        ) : null}
        <div className="recent-grid">
          {recentBooks.map((book) => (
            <RecentBookCard key={book.isbn} book={book} />
          ))}
        </div>
      </section>
    </AppLayout>
  );
}

function ScanPage() {
  const navigate = useNavigate();
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const controlsRef = useRef<{ stop: () => void } | null>(null);
  const [message, setMessage] = useState(
    "裏表紙の ISBN バーコードを枠に合わせてください。読み取り後は自動で判定画面へ移動します。",
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
        setMessage("ISBN バーコードを判定できませんでした。少し距離をとって再度お試しください。");
        return;
      }

      detected = true;
      controlsRef.current?.stop();
      setMessage(`ISBN ${isbn} を読み取りました。判定画面へ移動しています...`);
      if (active) {
        navigate(`/result/${isbn}`);
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
              setMessage(`読み取り中にエラーが発生しました: ${error.message}`);
            }
          },
        );

        controlsRef.current = controls;
        setMessage("バーコードを枠の中央に合わせてください。少し離して固定すると読み取りやすくなります。");
      } catch (error) {
        const detail = error instanceof Error ? error.message : String(error);
        if (/Permission|denied|NotAllowed/i.test(detail)) {
          setMessage("カメラ権限が拒否されています。ブラウザ設定でカメラ利用を許可してください。");
          return;
        }
        if (/secure|https|origin/i.test(detail)) {
          setMessage("カメラは HTTPS または localhost でのみ利用できます。");
          return;
        }
        setMessage(`カメラを利用できません: ${detail}`);
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
    <AppLayout title="スキャン" subtitle="いつでも登録できる常設アクション">
      <section className="panel scan-panel">
        <div className="section-heading">
          <div>
            <p className="section-label">ISBN スキャン</p>
            <h3>重複購入をその場で確認</h3>
          </div>
        </div>
        <p className="subtle">{message}</p>
        <ul className="scan-tips">
          <li>裏表紙の ISBN バーコードを横向きのまま枠に合わせてください。</li>
          <li>近づけすぎるとピントが合いにくいので、少し離して固定すると安定します。</li>
          <li>影が入らない明るい場所だと反応しやすくなります。</li>
        </ul>
        <div className="scanner-shell">
          <video ref={videoRef} className="scanner-video" muted playsInline autoPlay />
          <div className="scanner-overlay" aria-hidden="true">
            <div className="scanner-target" />
          </div>
        </div>
      </section>
    </AppLayout>
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
  const [bookFormat, setBookFormat] = useState<BookFormat>(defaultBookFormat);
  const [category, setCategory] = useState<Category>(defaultCategory);
  const [readingStatus, setReadingStatus] = useState<ReadingStatus>(defaultReadingStatus);

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
          setMessage("書籍状態の確認に失敗しました。");
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
            setMessage("書誌情報の取得が混み合っています。少し待ってから再試行してください。");
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
        readingStatus,
      });
      navigate(`/books/${isbn}`, { replace: true });
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setRegistered(true);
        setMessage("この本はすでに登録されています。");
      } else {
        setMessage("登録に失敗しました。");
      }
    }
  };

  return (
    <AppLayout title="判定結果" subtitle={`ISBN ${isbn}`}>
      <section className={`panel result-banner ${registered ? "is-registered" : "is-unregistered"}`}>
        <p className="section-label">判定ステータス</p>
        <h2>{loading ? "確認中..." : registered ? "この本はすでに登録されています" : "この本は未登録です"}</h2>
        {message ? <p className="subtle">{message}</p> : null}
      </section>

      <section className="panel detail-panel">
        <div className="section-heading">
          <div>
            <p className="section-label">書誌情報</p>
            <h3>登録前に内容を確認</h3>
          </div>
        </div>
        {loading ? <p className="empty-copy">書誌情報を取得しています...</p> : null}
        {!loading && lookupFailed ? (
          <p className="empty-copy">Google Books API から書誌情報を取得できませんでした。</p>
        ) : null}
        {!loading && book ? (
          <>
            <div className="detail-grid">
              <CoverArt book={book} large />
              <div className="detail-copy">
                <h2>{book.title || "タイトル未設定"}</h2>
                <p><strong>著者:</strong> {book.author || "-"}</p>
                <p><strong>出版社:</strong> {book.publisher || "-"}</p>
                <p><strong>出版日:</strong> {book.publishedDate || "-"}</p>
                <p><strong>分類:</strong> {"bookFormat" in book ? book.bookFormat : bookFormat}</p>
                <p><strong>カテゴリ:</strong> {"category" in book ? book.category : category}</p>
                <p><strong>読書ステータス:</strong> {"readingStatus" in book ? book.readingStatus : readingStatus}</p>
              </div>
            </div>
            {!registered ? (
              <>
                <div className="classification-grid">
                  <label>
                    <span>形態</span>
                    <select value={bookFormat} onChange={(event) => setBookFormat(event.target.value as BookFormat)}>
                      {bookFormats.map((item) => (
                        <option key={item} value={item}>{item}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span>ジャンル</span>
                    <select value={category} onChange={(event) => setCategory(event.target.value as Category)}>
                      {categories.map((item) => (
                        <option key={item} value={item}>{item}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span>読書ステータス</span>
                    <select
                      value={readingStatus}
                      onChange={(event) => setReadingStatus(event.target.value as ReadingStatus)}
                    >
                      {readingStatuses.map((item) => (
                        <option key={item} value={item}>{item}</option>
                      ))}
                    </select>
                  </label>
                </div>
                <button className="primary-pill" onClick={() => void handleCreate()}>
                  蔵書に登録する
                </button>
              </>
            ) : null}
          </>
        ) : null}
      </section>
    </AppLayout>
  );
}

function BooksPage({ accessToken }: { accessToken: string }) {
  const location = useLocation();
  const navigate = useNavigate();
  const params = new URLSearchParams(location.search);
  const query = params.get("q") ?? "";
  const bookFormat = params.get("bookFormat") ?? "";
  const category = params.get("category") ?? "";
  const readingStatus = params.get("readingStatus") ?? "";
  const sort = (params.get("sort") as SortOption | null) ?? "newest";

  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchText, setSearchText] = useState(query);
  const [bookFormatFilter, setBookFormatFilter] = useState(bookFormat);
  const [categoryFilter, setCategoryFilter] = useState(category);
  const [readingStatusFilter, setReadingStatusFilter] = useState(readingStatus);
  const [sortValue, setSortValue] = useState<SortOption>(sort);
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    setSearchText(query);
    setBookFormatFilter(bookFormat);
    setCategoryFilter(category);
    setReadingStatusFilter(readingStatus);
    setSortValue(sort);
  }, [query, bookFormat, category, readingStatus, sort]);

  useEffect(() => {
    const load = async (): Promise<void> => {
      setLoading(true);
      try {
        const result = await getBooks(accessToken, { query, bookFormat, category, readingStatus });
        const sorted = sortBooks(result.items, sort);
        setBooks(sorted);
        setActiveIndex(sorted.length > 0 ? Math.floor((sorted.length - 1) / 2) : 0);
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, [accessToken, query, bookFormat, category, readingStatus, sort]);

  const applyFilters = (): void => {
    const nextParams = new URLSearchParams();
    if (searchText.trim()) nextParams.set("q", searchText.trim());
    if (bookFormatFilter) nextParams.set("bookFormat", bookFormatFilter);
    if (categoryFilter) nextParams.set("category", categoryFilter);
    if (readingStatusFilter) nextParams.set("readingStatus", readingStatusFilter);
    if (sortValue !== "newest") nextParams.set("sort", sortValue);
    navigate(`/books${nextParams.toString() ? `?${nextParams.toString()}` : ""}`);
  };

  return (
    <AppLayout title="蔵書一覧" subtitle="本棚を眺めるように管理する">
      <section className="panel library-toolbar">
        <div className="library-toolbar-main">
          <div className="stat-chip">
            <strong>{books.length}</strong>
            <span>Books</span>
          </div>
          <SearchBar
            value={searchText}
            onChange={setSearchText}
            placeholder="タイトル・著者で検索"
            submitLabel="検索"
            onSubmit={applyFilters}
          />
        </div>
        <div className="toolbar-controls">
          <label>
            <span>並び替え</span>
            <select value={sortValue} onChange={(event) => setSortValue(event.target.value as SortOption)}>
              {sortOptions.map((item) => (
                <option key={item.value} value={item.value}>{item.label}</option>
              ))}
            </select>
          </label>
          <label>
            <span>カテゴリ</span>
            <select value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}>
              <option value="">すべて</option>
              {categories.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>
          </label>
          <label>
            <span>形態</span>
            <select value={bookFormatFilter} onChange={(event) => setBookFormatFilter(event.target.value)}>
              <option value="">すべて</option>
              {bookFormats.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>
          </label>
          <label>
            <span>読書ステータス</span>
            <select value={readingStatusFilter} onChange={(event) => setReadingStatusFilter(event.target.value)}>
              <option value="">すべて</option>
              {readingStatuses.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>
          </label>
          <button className="secondary-pill" onClick={applyFilters}>
            絞り込む
          </button>
        </div>
      </section>

      <section className="bookshelf-section">
        {loading ? <div className="panel empty-state">本棚を読み込んでいます...</div> : null}
        {!loading && books.length === 0 ? (
          <div className="panel empty-state">
            <p>条件に合う蔵書はありません。</p>
            <p className="subtle">検索語やフィルタを変更するか、右下のボタンから新しく登録してください。</p>
          </div>
        ) : null}
        {!loading && books.length > 0 ? (
          <CoverFlowShelf books={books} activeIndex={activeIndex} onActiveIndexChange={setActiveIndex} />
        ) : null}
      </section>
    </AppLayout>
  );
}

function BookDetailPage({ accessToken }: { accessToken: string }) {
  const { isbn = "" } = useParams();
  const navigate = useNavigate();
  const [book, setBook] = useState<Book | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [readingStatus, setReadingStatus] = useState<ReadingStatus>(defaultReadingStatus);
  const [savingStatus, setSavingStatus] = useState(false);

  useEffect(() => {
    const load = async (): Promise<void> => {
      try {
        const result = await getBook(accessToken, isbn);
        setBook(result);
        setReadingStatus(result.readingStatus);
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
    if (!window.confirm("この書籍を蔵書から削除しますか？")) {
      return;
    }

    try {
      await deleteBook(accessToken, isbn);
      navigate("/books", { replace: true });
    } catch {
      setMessage("削除に失敗しました。");
    }
  };

  const handleUpdateReadingStatus = async (): Promise<void> => {
    if (!book) {
      return;
    }

    setSavingStatus(true);
    setMessage(null);

    try {
      const updated = await updateBookStatus(accessToken, isbn, readingStatus);
      setBook(updated);
      setReadingStatus(updated.readingStatus);
      setMessage("読書ステータスを更新しました。");
    } catch {
      setMessage("読書ステータスの更新に失敗しました。");
    } finally {
      setSavingStatus(false);
    }
  };

  return (
    <AppLayout title="書籍詳細" subtitle={book?.title ?? "蔵書の詳細を見る"}>
      <section className="panel detail-panel">
        {loading ? <p className="empty-copy">書籍情報を読み込んでいます...</p> : null}
        {message ? <p className="subtle">{message}</p> : null}
        {notFound ? (
          <p>
            <Link className="text-link" to="/books">蔵書一覧へ戻る</Link>
          </p>
        ) : null}
        {book ? (
          <>
            <div className="detail-grid">
              <CoverArt book={book} large />
              <div className="detail-copy">
                <div className="chip-row">
                  <TagChip>{book.category}</TagChip>
                  <TagChip tone="outline">{book.bookFormat}</TagChip>
                  <TagChip>{book.readingStatus}</TagChip>
                </div>
                <h2>{book.title}</h2>
                <p><strong>著者:</strong> {book.author || "-"}</p>
                <p><strong>出版社:</strong> {book.publisher || "-"}</p>
                <p><strong>出版日:</strong> {book.publishedDate || "-"}</p>
                <p><strong>ISBN:</strong> {book.isbn}</p>
                <p><strong>読書ステータス:</strong> {book.readingStatus}</p>
                <p><strong>登録日時:</strong> {formatDateTime(book.createdAt)}</p>
              </div>
            </div>
            <div className="classification-grid">
              <label>
                <span>読書ステータス</span>
                <select
                  value={readingStatus}
                  onChange={(event) => setReadingStatus(event.target.value as ReadingStatus)}
                  disabled={savingStatus}
                >
                  {readingStatuses.map((item) => (
                    <option key={item} value={item}>{item}</option>
                  ))}
                </select>
              </label>
            </div>
            <button className="primary-pill" onClick={() => void handleUpdateReadingStatus()} disabled={savingStatus}>
              {savingStatus ? "更新中..." : "ステータスを保存"}
            </button>
            <button className="danger-pill" onClick={() => void handleDelete()}>
              削除する
            </button>
          </>
        ) : null}
      </section>
    </AppLayout>
  );
}

function SummaryCards({
  items,
}: {
  items: Array<{ label: string; value: string; caption: string; tone: "teal" | "sky" | "amber" }>;
}) {
  return (
    <div className="summary-grid">
      {items.map((item) => (
        <article key={item.label} className={`summary-card tone-${item.tone}`}>
          <p>{item.label}</p>
          <strong>{item.value}</strong>
          <span>{item.caption}</span>
        </article>
      ))}
    </div>
  );
}

function SearchBar({
  value,
  onChange,
  onSubmit,
  placeholder,
  submitLabel,
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  placeholder: string;
  submitLabel: string;
}) {
  return (
    <form
      className="search-bar"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <SearchIcon />
      <input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} aria-label={placeholder} />
      <button type="submit" className="inline-search-action">
        {submitLabel}
      </button>
    </form>
  );
}

function RecentBookCard({ book }: { book: Book }) {
  return (
    <Link to={`/books/${book.isbn}`} className="recent-book-card">
      <div className="recent-cover-wrap">
        <CoverArt book={book} />
      </div>
      <div className="recent-card-copy">
        <div className="chip-row">
          <TagChip>{book.category}</TagChip>
          <TagChip tone="outline">{book.bookFormat}</TagChip>
          <TagChip>{book.readingStatus}</TagChip>
        </div>
        <h4 title={book.title}>{book.title || "タイトル未設定"}</h4>
        <p className="author-line">{book.author || "著者情報なし"}</p>
        <p className="subtle">{formatDateTime(book.createdAt)}</p>
      </div>
    </Link>
  );
}

function FloatingScanButton() {
  return (
    <Link to="/scan" className="fab-scan">
      <ScanIcon />
      <span>スキャンする</span>
    </Link>
  );
}

function BookshelfRow({
  books,
  selectedIsbn,
  onSelect,
}: {
  books: Book[];
  selectedIsbn: string | null;
  onSelect: (isbn: string | null) => void;
}) {
  return (
    <section className="bookshelf-row">
      <div className="bookshelf-backboard" />
      <div className="bookshelf-track">
        {books.map((book) => {
          const isSelected = selectedIsbn === book.isbn;
          const hasCoverImage = Boolean(book.coverImageUrl);

          return (
            <article key={book.isbn} className={`bookshelf-book ${isSelected ? "is-selected" : ""}`}>
              <button
                type="button"
                className="bookshelf-spine"
                onClick={() => onSelect(isSelected ? null : book.isbn)}
                aria-expanded={isSelected}
              >
                <CoverArt book={book} className="bookshelf-cover-art" />
                <span className="bookshelf-cover-shadow" aria-hidden="true" />
                {!hasCoverImage ? (
                  <span className="spine-accent" style={{ background: coverAccent(book.isbn) }} />
                ) : null}
                <span className="bookshelf-spine-copy">
                  <span className="spine-title" title={book.title}>{book.title || "タイトル未設定"}</span>
                  <span className="spine-author">{book.author || "著者不明"}</span>
                </span>
              </button>
              <div className="bookshelf-face">
                <Link to={`/books/${book.isbn}`} className="bookshelf-face-link">
                  <CoverArt book={book} />
                  <div className="bookshelf-face-copy">
                    <div className="chip-row">
                      <TagChip>{book.category}</TagChip>
                      <TagChip tone="outline">{book.bookFormat}</TagChip>
                      <TagChip>{book.readingStatus}</TagChip>
                    </div>
                    <strong title={book.title}>{book.title || "タイトル未設定"}</strong>
                    <span>{book.author || "著者情報なし"}</span>
                    <small>{formatDate(book.createdAt)}</small>
                  </div>
                </Link>
              </div>
            </article>
          );
        })}
      </div>
      <div className="bookshelf-plank" />
    </section>
  );
}

function CoverArt({
  book,
  large = false,
  className = "",
}: {
  book: Pick<Book, "title" | "coverImageUrl" | "isbn"> | BookLookupResult;
  large?: boolean;
  className?: string;
}) {
  const [imageFailed, setImageFailed] = useState(false);

  useEffect(() => {
    setImageFailed(false);
  }, [book.coverImageUrl, book.isbn]);

  if (book.coverImageUrl && !imageFailed) {
    return (
      <img
        className={`cover-art ${large ? "large" : ""} ${className}`.trim()}
        src={book.coverImageUrl}
        alt={book.title || "書影"}
        loading="lazy"
        onError={() => setImageFailed(true)}
      />
    );
  }

  return (
    <div className={`cover-fallback ${large ? "large" : ""} ${className}`.trim()} style={{ background: coverAccent(book.isbn) }}>
      <span>{book.title ? book.title.slice(0, 24) : "NO IMAGE"}</span>
    </div>
  );
}

function TagChip({ children, tone = "solid" }: { children: ReactNode; tone?: "solid" | "outline" }) {
  return <span className={`tag-chip ${tone === "outline" ? "is-outline" : ""}`}>{children}</span>;
}

function SearchIcon() {
  return (
    <svg className="icon search-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M10.5 4a6.5 6.5 0 1 0 4.1 11.54l4.43 4.43 1.41-1.41-4.43-4.43A6.5 6.5 0 0 0 10.5 4Zm0 2a4.5 4.5 0 1 1 0 9 4.5 4.5 0 0 1 0-9Z" fill="currentColor" />
    </svg>
  );
}

function ScanIcon() {
  return (
    <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 7a3 3 0 0 1 3-3h2v2H7a1 1 0 0 0-1 1v2H4V7Zm13-3h-2v2h2a1 1 0 0 1 1 1v2h2V7a3 3 0 0 0-3-3ZM6 15H4v2a3 3 0 0 0 3 3h2v-2H7a1 1 0 0 1-1-1v-2Zm14 0h-2v2a1 1 0 0 1-1 1h-2v2h2a3 3 0 0 0 3-3v-2ZM7 10h2v4H7v-4Zm4-1h2v6h-2V9Zm4 1h2v4h-2v-4Z" fill="currentColor" />
    </svg>
  );
}

function sortBooks(books: Book[], sort: SortOption): Book[] {
  const next = [...books];
  next.sort((left, right) => {
    if (sort === "oldest") return left.createdAt.localeCompare(right.createdAt);
    if (sort === "title") return left.title.localeCompare(right.title, "ja");
    if (sort === "author") return left.author.localeCompare(right.author, "ja");
    return right.createdAt.localeCompare(left.createdAt);
  });
  return next;
}

function isInCurrentMonth(value: string): boolean {
  const date = new Date(value);
  const now = new Date();
  return date.getFullYear() === now.getFullYear() && date.getMonth() === now.getMonth();
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("ja-JP", { month: "numeric", day: "numeric", hour: "numeric", minute: "2-digit" }).format(new Date(value));
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("ja-JP", { year: "numeric", month: "numeric", day: "numeric" }).format(new Date(value));
}

function formatRelativeTime(value: string): string {
  const delta = new Date(value).getTime() - Date.now();
  const minutes = Math.round(delta / (1000 * 60));
  const hours = Math.round(delta / (1000 * 60 * 60));
  const days = Math.round(delta / (1000 * 60 * 60 * 24));
  const formatter = new Intl.RelativeTimeFormat("ja", { numeric: "auto" });
  if (Math.abs(minutes) < 60) return formatter.format(minutes, "minute");
  if (Math.abs(hours) < 24) return formatter.format(hours, "hour");
  return formatter.format(days, "day");
}

function chunkBooks(books: Book[], chunkSize: number): Book[][] {
  const chunks: Book[][] = [];
  for (let index = 0; index < books.length; index += chunkSize) {
    chunks.push(books.slice(index, index + chunkSize));
  }
  return chunks;
}

function coverAccent(seed: string): string {
  const palettes = [
    "linear-gradient(180deg, #2aa3a7 0%, #14656e 100%)",
    "linear-gradient(180deg, #81c7d4 0%, #4f95ab 100%)",
    "linear-gradient(180deg, #f2c66c 0%, #d38e31 100%)",
    "linear-gradient(180deg, #7fc0a9 0%, #4e8873 100%)",
    "linear-gradient(180deg, #9eb7df 0%, #607fa9 100%)",
  ];
  const total = [...seed].reduce((sum, char) => sum + char.charCodeAt(0), 0);
  return palettes[total % palettes.length];
}

export default App;
