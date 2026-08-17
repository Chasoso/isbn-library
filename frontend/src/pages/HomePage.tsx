import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AppLayout } from "../app-shell";
import { getBooks } from "../lib/api";
import { readingStatuses } from "../readingStatus";
import type { AuthState, Book } from "../types";
import { RecentBookCard, SearchBar, sortBooks } from "../view-helpers";

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
    <AppLayout title="ホーム">
      <section className="panel dashboard-hero">
        <dl className="shelf-summary" aria-label="本棚の概要">
          <div className="shelf-summary__item">
            <dt>総冊数</dt>
            <dd>
              <strong>{books.length}</strong>
              <span>冊</span>
            </dd>
          </div>
          <div className="shelf-summary__item">
            <dt>未読</dt>
            <dd>
              <strong>{unreadCount}</strong>
              <span>冊</span>
            </dd>
          </div>
        </dl>
      </section>

      <section className="panel search-panel home-search-panel">
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
          <h3>新しく棚に並んだ本</h3>
          <Link className="text-link" to="/books">
            蔵書一覧を見る
          </Link>
        </div>
        {loading ? <p className="empty-copy">蔵書を読み込み中...</p> : null}
        {!loading && recentBooks.length === 0 ? (
          <div className="empty-state">
            <p>まだ本が登録されていません。</p>
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
