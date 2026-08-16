import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { bookFormats } from "../catalog";
import { AppLayout } from "../app-shell";
import { CoverFlowShelf } from "../components/CoverFlowShelf";
import { getBooks, getCategories } from "../lib/api";
import { readingStatuses } from "../readingStatus";
import type { Book, CategoryDefinition } from "../types";
import { sortBooks } from "../view-helpers";

const sortOptions = [
  { value: "newest", label: "Newest" },
  { value: "oldest", label: "Oldest" },
  { value: "title", label: "Title" },
  { value: "author", label: "Author" },
] as const;

type SortOption = (typeof sortOptions)[number]["value"];
type ViewMode = "grid" | "list";

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
  const [view, setView] = useState<ViewMode>("grid");
  const [activeIndex, setActiveIndex] = useState(0);
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

  const activeChips = [
    sortValue !== "newest" ? sortOptions.find((item) => item.value === sortValue)?.label : "",
    bookFormatFilter,
    categoryFilter ? categories.find((item) => item.categoryId === categoryFilter)?.name ?? categoryFilter : "",
    readingStatusFilter,
  ].filter(Boolean);

  return (
    <AppLayout title="Books" subtitle="Search, filter, and browse the shelf.">
      <section className="panel library-tools">
        <div className="search-box">
          <span aria-hidden="true">⌕</span>
          <input
            value={searchText}
            onChange={(event) => setSearchText(event.target.value)}
            placeholder="Search title or author"
            aria-label="Search title or author"
          />
          <button
            type="button"
            onClick={() => {
              const nextSearch = buildFilterSearch();
              navigate(`/books${nextSearch ? `?${nextSearch}` : ""}`, { replace: true });
            }}
          >
            Search
          </button>
        </div>

        <div className="desktop-filters">
          <div className="toolbar-controls">
            <label>
              <span>Sort</span>
              <select value={sortValue} onChange={(event) => setSortValue(event.target.value as SortOption)}>
                {sortOptions.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Category</span>
              <select value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}>
                <option value="">All</option>
                {categories.map((item) => (
                  <option key={item.categoryId} value={item.categoryId}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Format</span>
              <select value={bookFormatFilter} onChange={(event) => setBookFormatFilter(event.target.value)}>
                <option value="">All</option>
                {bookFormats.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Status</span>
              <select value={readingStatusFilter} onChange={(event) => setReadingStatusFilter(event.target.value)}>
                <option value="">All</option>
                {readingStatuses.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>
            <Link className="secondary-pill category-manage-link" to="/categories">
              Manage categories
            </Link>
          </div>
        </div>

        <div className="mobile-tool-row">
          <button className="filter-button" type="button" onClick={() => setFilterOpen(true)}>
            Filters
            {activeChips.length > 0 ? <b>{activeChips.length}</b> : null}
          </button>
          <div className="view-toggle">
            <button className={view === "grid" ? "active" : ""} type="button" onClick={() => setView("grid")}>
              Grid
            </button>
            <button className={view === "list" ? "active" : ""} type="button" onClick={() => setView("list")}>
              List
            </button>
          </div>
        </div>

        {activeChips.length > 0 ? (
          <div className="active-chips">
            {activeChips.map((chip) => (
              <span key={chip}>{chip}</span>
            ))}
            <button
              type="button"
              onClick={() => {
                setSearchText("");
                setBookFormatFilter("");
                setCategoryFilter("");
                setReadingStatusFilter("");
                setSortValue("newest");
              }}
            >
              Clear
            </button>
          </div>
        ) : null}
      </section>

      <section className="panel results-section">
        <div className="results-heading">
          <p>
            <strong>{books.length}</strong> books
          </p>
          <div className="desktop-view-toggle view-toggle">
            <button className={view === "grid" ? "active" : ""} type="button" onClick={() => setView("grid")}>
              Grid
            </button>
            <button className={view === "list" ? "active" : ""} type="button" onClick={() => setView("list")}>
              List
            </button>
          </div>
        </div>

        {loading ? <div className="empty-state">Loading books...</div> : null}
        {!loading && books.length === 0 ? (
          <div className="empty-state">
            <h3>No books found</h3>
            <p>Try another search or loosen the filters.</p>
          </div>
        ) : null}
        {!loading && books.length > 0 ? (
          <CoverFlowShelf
            books={books}
            activeIndex={activeIndex}
            onActiveIndexChange={setActiveIndex}
            layout={view}
          />
        ) : null}
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
                <h2 id="books-filter-title">Refine the shelf</h2>
              </div>
              <button
                type="button"
                className="icon-button"
                onClick={() => setFilterOpen(false)}
                aria-label="Close filters"
              >
                ×
              </button>
            </div>
            <div className="filter-fields">
              <label>
                <span>Sort</span>
                <select value={sortValue} onChange={(event) => setSortValue(event.target.value as SortOption)}>
                  {sortOptions.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>Category</span>
                <select value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}>
                  <option value="">All</option>
                  {categories.map((item) => (
                    <option key={item.categoryId} value={item.categoryId}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>Format</span>
                <select value={bookFormatFilter} onChange={(event) => setBookFormatFilter(event.target.value)}>
                  <option value="">All</option>
                  {bookFormats.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>Status</span>
                <select
                  value={readingStatusFilter}
                  onChange={(event) => setReadingStatusFilter(event.target.value)}
                >
                  <option value="">All</option>
                  {readingStatuses.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="sheet-actions">
              <button
                type="button"
                className="ghost-button"
                onClick={() => {
                  setSearchText("");
                  setBookFormatFilter("");
                  setCategoryFilter("");
                  setReadingStatusFilter("");
                  setSortValue("newest");
                }}
              >
                Reset
              </button>
              <button type="button" className="primary-button" onClick={() => setFilterOpen(false)}>
                Show {books.length} books
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </AppLayout>
  );
}
