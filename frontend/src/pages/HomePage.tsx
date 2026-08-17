import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AppLayout } from "../app-shell";
import { getBooks } from "../lib/api";
import { readingStatuses } from "../readingStatus";
import type { AuthState, Book } from "../types";
import { RecentBookCard, SearchBar, SummaryCards, sortBooks } from "../view-helpers";

const unreadStatus = readingStatuses[0];

function useCompactLayout(): boolean {
  const [compact, setCompact] = useState(() =>
    typeof window !== "undefined" ? window.matchMedia("(max-width: 480px)").matches : false,
  );

  useEffect(() => {
    const media = window.matchMedia("(max-width: 480px)");
    const update = () => setCompact(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);

  return compact;
}

export function HomePage({ authState }: { authState: AuthState }) {
  const navigate = useNavigate();
  const compact = useCompactLayout();
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

  const recentBooks = books.slice(0, 3);
  const unreadCount = books.filter((book) => book.readingStatus === unreadStatus).length;

  return (
    <AppLayout
      title="ホーム"
      subtitle={`${authState.name ?? "デモユーザー"}の蔵書を確認します`}
    >
      <section className="panel dashboard-hero">
        <div className="hero-copy">
          <p className="section-label">あなたの本棚</p>
          <h2>棚の状態をひと目でつかむ</h2>
          <p className="subtle">
            冊数、未読数、新着本をまとめて見渡せます。検索してすぐに本へ移動できます。
          </p>
        </div>

        <SummaryCards
          compact={compact}
          items={[
            {
              label: "総冊数",
              value: `${books.length}`,
              tone: "teal",
              caption: books.length > 0 ? "蔵書を管理中" : "まだ本がありません",
            },
            {
              label: "未読数",
              value: `${unreadCount}`,
              tone: "sky",
              caption: unreadCount > 0 ? "次に読む本" : "未読はありません",
            },
          ]}
        />
      </section>

      <section className="panel search-panel home-search-panel">
        <div className="section-heading">
          <div>
            <p className="section-label">検索</p>
            <h3>すぐに本を探す</h3>
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

      <section className="panel recent-section">
        <div className="section-heading">
          <div>
            <p className="section-label">最近追加</p>
            <h3>新しく棚に並んだ本</h3>
          </div>
          <Link className="text-link" to="/books">
            蔵書一覧を見る
          </Link>
        </div>
        {loading ? <p className="empty-copy">蔵書を読み込み中です...</p> : null}
        {!loading && recentBooks.length === 0 ? (
          <div className="empty-state">
            <p>まだ本が登録されていません。</p>
            <p className="subtle">右上のスキャンから ISBN を登録できます。</p>
          </div>
        ) : null}
        <div className="recent-grid">
          {recentBooks.map((book) => (
            <RecentBookCard key={book.isbn} book={book} compact={compact} />
          ))}
        </div>
      </section>
    </AppLayout>
  );
}
