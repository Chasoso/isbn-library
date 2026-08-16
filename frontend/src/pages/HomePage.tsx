import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AppLayout } from "../app-shell";
import { getBooks } from "../lib/api";
import { readingStatuses } from "../readingStatus";
import type { AuthState, Book } from "../types";
import { RecentBookCard, SearchBar, SummaryCards, sortBooks } from "../view-helpers";

const unreadStatus = readingStatuses[0];

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

  const recentBooks = books.slice(0, 3);
  const unreadCount = books.filter((book) => book.readingStatus === unreadStatus).length;

  return (
    <AppLayout
      title="ホーム"
      subtitle={`${authState.name ?? "アカウント"}さんの蔵書ダッシュボード`}
    >
      <section className="dashboard-hero panel">
        <div className="hero-copy">
          <p className="section-label">あなたの蔵書</p>
          <h2>棚の状態をひと目でつかむ</h2>
          <p className="subtle">
            冊数、未読数、新着本をまとめて見渡せます。次に読む本もすぐ検索できます。
          </p>
        </div>

        <SummaryCards
          items={[
            {
              label: "総冊数",
              value: `${books.length}`,
              tone: "teal",
              caption: books.length > 0 ? "蔵書を管理中" : "まずは1冊登録しましょう",
            },
            {
              label: "未読数",
              value: `${unreadCount}`,
              tone: "sky",
              caption: unreadCount > 0 ? "次に読みたい本" : "未読の本はありません",
            },
          ]}
        />
      </section>

      <section className="panel search-panel">
        <div className="section-heading">
          <div>
            <p className="section-label">検索</p>
            <h3>次に読みたい本をすぐ探す</h3>
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
            <p className="subtle">右上のスキャンか、蔵書一覧から追加できます。</p>
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
