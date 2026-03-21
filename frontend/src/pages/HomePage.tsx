import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AppLayout } from "../app-shell";
import { getBooks } from "../lib/api";
import type { AuthState, Book } from "../types";
import { RecentBookCard, SearchBar, SummaryCards, isInCurrentMonth, sortBooks } from "../view-helpers";

export function HomePage({ authState }: { authState: AuthState }) {
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

  return (
    <AppLayout
      title="ホーム"
      subtitle={authState.name ? `${authState.name}さんの蔵書ダッシュボード` : null}
    >
      <section className="dashboard-hero panel">
        <div className="hero-copy">
          <p className="section-label">あなたの蔵書</p>
          <h2>本棚の状態をひと目で把握</h2>
          <p className="subtle">
            重複購入の確認だけでなく、最近追加した本や分類の広がりまで、今の蔵書を
            気持ちよく眺められるホームです。
          </p>
        </div>
        <SummaryCards
          items={[
            {
              label: "総冊数",
              value: `${books.length}`,
              tone: "teal",
              caption: books.length > 0 ? "蔵書を管理中" : "まずは1冊登録",
            },
            {
              label: "今月の追加",
              value: `+${monthlyCount}`,
              tone: "sky",
              caption: monthlyCount > 0 ? "今月の登録数" : "追加はまだありません",
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
        {loading ? <p className="empty-copy">蔵書を読み込み中です...</p> : null}
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
