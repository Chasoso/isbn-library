import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { bookFormats } from "../catalog";
import { AppLayout } from "../app-shell";
import { CoverFlowShelf } from "../components/CoverFlowShelf";
import { getBooks, getCategories } from "../lib/api";
import { readingStatuses } from "../readingStatus";
import type { Book, CategoryDefinition } from "../types";
import { sortBooks, SearchBar } from "../view-helpers";

const sortOptions = [
  { value: "newest", label: "新しい順" },
  { value: "oldest", label: "古い順" },
  { value: "title", label: "タイトル順" },
  { value: "author", label: "著者順" },
] as const;

type SortOption = (typeof sortOptions)[number]["value"];
type ViewMode = "grid" | "list";

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

export function BooksPage({ accessToken }: { accessToken: string }) {
  const compact = useCompactLayout();
  const location = useLocation();
  const navigate = useNavigate();
  const params = new URLSearchParams(location.search);
  const query = params.get("q") ?? "";
  const bookFormat = params.get("bookFormat") ?? "";
  const categoryId = params.get("categoryId") ?? "";
  const readingStatus = params.get("readingStatus") ?? "";
  const sort = (params.get("sort") as SortOption | null) ?? "newest";

  const [books, setBooks] = useState<Book[]>([]);
  const [categories, setCategories] = useState<CategoryDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchText, setSearchText] = useState(query);
  const [bookFormatFilter, setBookFormatFilter] = useState(bookFormat);
  const [categoryFilter, setCategoryFilter] = useState(categoryId);
  const [readingStatusFilter, setReadingStatusFilter] = useState(readingStatus);
  const [sortValue, setSortValue] = useState<SortOption>(sort);
  const [view, setView] = useState<ViewMode>(
    compact || (typeof window !== "undefined" && window.matchMedia("(max-width: 719px)").matches)
      ? "list"
      : "grid",
  );
  const [filterOpen, setFilterOpen] = useState(false);

  useEffect(() => {
    setSearchText(query);
    setBookFormatFilter(bookFormat);
    setCategoryFilter(categoryId);
    setReadingStatusFilter(readingStatus);
    setSortValue(sort);
  }, [query, bookFormat, categoryId, readingStatus, sort]);

  useEffect(() => {
    const loadCategories = async (): Promise<void> => {
      try {
        const result = await getCategories(accessToken);
        setCategories(result.items);
      } catch {
        setCategories([]);
      }
    };

    void loadCategories();
  }, [accessToken]);

  useEffect(() => {
    const load = async (): Promise<void> => {
      setLoading(true);
      try {
        const result = await getBooks(accessToken, {
          query,
          bookFormat,
          categoryId,
          readingStatus,
        });
        setBooks(sortBooks(result.items, sort));
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, [accessToken, query, bookFormat, categoryId, readingStatus, sort]);

  const buildFilterSearch = (): string => {
    const nextParams = new URLSearchParams();
    if (searchText.trim()) nextParams.set("q", searchText.trim());
    if (bookFormatFilter) nextParams.set("bookFormat", bookFormatFilter);
    if (categoryFilter) nextParams.set("categoryId", categoryFilter);
    if (readingStatusFilter) nextParams.set("readingStatus", readingStatusFilter);
    if (sortValue !== "newest") nextParams.set("sort", sortValue);
    return nextParams.toString();
  };

  useEffect(() => {
    const handle = window.setTimeout(() => {
      const nextSearch = buildFilterSearch();
      const currentSearch = location.search.startsWith("?") ? location.search.slice(1) : location.search;
      if (nextSearch === currentSearch) {
        return;
      }
      navigate(`/books${nextSearch ? `?${nextSearch}` : ""}`, { replace: true });
    }, 180);

    return () => window.clearTimeout(handle);
  }, [searchText, bookFormatFilter, categoryFilter, readingStatusFilter, sortValue, location.search, navigate]);

  const activeChips = [
    sortValue !== "newest" ? sortOptions.find((item) => item.value === sortValue)?.label : "",
    bookFormatFilter,
    categoryFilter ? categories.find((item) => item.categoryId === categoryFilter)?.name ?? categoryFilter : "",
    readingStatusFilter,
  ].filter(Boolean);

  const applyFilters = (): void => {
    const nextSearch = buildFilterSearch();
    navigate(`/books${nextSearch ? `?${nextSearch}` : ""}`, { replace: true });
  };

  const resetFilters = (): void => {
    setSearchText("");
    setBookFormatFilter("");
    setCategoryFilter("");
    setReadingStatusFilter("");
    setSortValue("newest");
  };

  return (
    <AppLayout title="蔵書一覧" subtitle="検索、絞り込み、並び替えをひとつの画面で行えます。">
      <section className="panel library-tools">
        <div className="books-search-strip">
          <SearchBar
            value={searchText}
            onChange={setSearchText}
            placeholder="タイトル・著者で検索"
            submitLabel="検索"
            onSubmit={applyFilters}
          />

          <div className="mobile-tool-row">
            <button className="filter-button" type="button" onClick={() => setFilterOpen(true)}>
              絞り込み
              {activeChips.length > 0 ? <b>{activeChips.length}</b> : null}
            </button>
            <div className="view-toggle" role="group" aria-label="表示切り替え">
              <button className={view === "grid" ? "active" : ""} type="button" onClick={() => setView("grid")}>
                グリッド
              </button>
              <button className={view === "list" ? "active" : ""} type="button" onClick={() => setView("list")}>
                リスト
              </button>
            </div>
            <p className="books-count">{books.length}冊</p>
          </div>
        </div>

        <div className="desktop-filters">
          <div className="toolbar-controls">
            <label>
              <span>並び替え</span>
              <select value={sortValue} onChange={(event) => setSortValue(event.target.value as SortOption)}>
                {sortOptions.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>カテゴリ</span>
              <select value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}>
                <option value="">すべて</option>
                {categories.map((item) => (
                  <option key={item.categoryId} value={item.categoryId}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>形態</span>
              <select value={bookFormatFilter} onChange={(event) => setBookFormatFilter(event.target.value)}>
                <option value="">すべて</option>
                {bookFormats.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>読書ステータス</span>
              <select value={readingStatusFilter} onChange={(event) => setReadingStatusFilter(event.target.value)}>
                <option value="">すべて</option>
                {readingStatuses.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>
            <Link className="secondary-pill category-manage-link" to="/categories">
              カテゴリ管理
            </Link>
          </div>
        </div>

        {activeChips.length > 0 ? (
          <div className="active-chips">
            {activeChips.map((chip) => (
              <span key={chip}>{chip}</span>
            ))}
            <button type="button" onClick={resetFilters}>
              条件を解除
            </button>
          </div>
        ) : null}
      </section>

      <section className="panel results-section">
        {!compact ? (
          <div className="results-heading">
            <p>
              <strong>{books.length}</strong>冊
            </p>
            <div className="desktop-view-toggle view-toggle">
              <button className={view === "grid" ? "active" : ""} type="button" onClick={() => setView("grid")}>
                グリッド
              </button>
              <button className={view === "list" ? "active" : ""} type="button" onClick={() => setView("list")}>
                リスト
              </button>
            </div>
          </div>
        ) : null}

        {loading ? <div className="empty-state">蔵書を読み込み中です...</div> : null}
        {!loading && books.length === 0 ? (
          <div className="empty-state">
            <h3>本が見つかりませんでした</h3>
            <p>検索や絞り込み条件を見直してください。</p>
          </div>
        ) : null}
        {!loading && books.length > 0 ? <CoverFlowShelf books={books} layout={view} /> : null}
      </section>

      {filterOpen ? (
        <div className="modal-backdrop" onMouseDown={() => setFilterOpen(false)}>
          <section
            className="filter-sheet"
            role="dialog"
            aria-modal="true"
            aria-labelledby="books-filter-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="sheet-heading">
              <div>
                <p className="eyebrow">FILTERS</p>
                <h2 id="books-filter-title">絞り込み</h2>
              </div>
              <button
                type="button"
                className="icon-button"
                onClick={() => setFilterOpen(false)}
                aria-label="絞り込みを閉じる"
              >
                ×
              </button>
            </div>
            <div className="filter-fields">
              <label>
                <span>並び替え</span>
                <select value={sortValue} onChange={(event) => setSortValue(event.target.value as SortOption)}>
                  {sortOptions.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>カテゴリ</span>
                <select value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}>
                  <option value="">すべて</option>
                  {categories.map((item) => (
                    <option key={item.categoryId} value={item.categoryId}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>形態</span>
                <select value={bookFormatFilter} onChange={(event) => setBookFormatFilter(event.target.value)}>
                  <option value="">すべて</option>
                  {bookFormats.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>読書ステータス</span>
                <select
                  value={readingStatusFilter}
                  onChange={(event) => setReadingStatusFilter(event.target.value)}
                >
                  <option value="">すべて</option>
                  {readingStatuses.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="sheet-actions">
              <button type="button" className="ghost-button" onClick={resetFilters}>
                解除
              </button>
              <button type="button" className="primary-button" onClick={() => setFilterOpen(false)}>
                {books.length}冊を表示
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </AppLayout>
  );
}
