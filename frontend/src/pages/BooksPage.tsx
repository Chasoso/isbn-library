import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { bookFormats } from "../catalog";
import { AppLayout } from "../app-shell";
import { CoverFlowShelf } from "../components/CoverFlowShelf";
import { getBooks, getCategories } from "../lib/api";
import { readingStatuses } from "../readingStatus";
import type { Book, CategoryDefinition } from "../types";
import { SearchBar, sortBooks } from "../view-helpers";

const sortOptions = [
  { value: "newest", label: "登録日が新しい順" },
  { value: "oldest", label: "登録日が古い順" },
  { value: "title", label: "タイトル順" },
  { value: "author", label: "著者順" },
] as const;

type SortOption = (typeof sortOptions)[number]["value"];

export function BooksPage({ accessToken }: { accessToken: string }) {
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
  const [activeIndex, setActiveIndex] = useState(0);

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
        const sorted = sortBooks(result.items, sort);
        setBooks(sorted);
        setActiveIndex(sorted.length > 0 ? Math.floor((sorted.length - 1) / 2) : 0);
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
      const currentSearch = location.search.startsWith("?")
        ? location.search.slice(1)
        : location.search;
      if (nextSearch === currentSearch) {
        return;
      }
      navigate(`/books${nextSearch ? `?${nextSearch}` : ""}`, { replace: true });
    }, 200);

    return () => window.clearTimeout(handle);
  }, [
    searchText,
    bookFormatFilter,
    categoryFilter,
    readingStatusFilter,
    sortValue,
    location.search,
    navigate,
  ]);

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
            onSubmit={() => {
              const nextSearch = buildFilterSearch();
              navigate(`/books${nextSearch ? `?${nextSearch}` : ""}`, { replace: true });
            }}
          />
        </div>
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
      </section>

      <section className="bookshelf-section">
        {loading ? <div className="panel empty-state">本棚を読み込み中です...</div> : null}
        {!loading && books.length === 0 ? (
          <div className="panel empty-state">
            <p>条件に合う蔵書はありません。</p>
            <p className="subtle">検索語やフィルタを変えるか、右下のボタンから新しく登録してください。</p>
          </div>
        ) : null}
        {!loading && books.length > 0 ? (
          <CoverFlowShelf books={books} activeIndex={activeIndex} onActiveIndexChange={setActiveIndex} />
        ) : null}
      </section>
    </AppLayout>
  );
}
