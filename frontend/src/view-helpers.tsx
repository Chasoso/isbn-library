import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import type { Book, BookLookupResult } from "./types";

export function SummaryCards({
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

export function SearchBar({
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

export function RecentBookCard({ book }: { book: Book }) {
  return (
    <Link to={`/books/${book.isbn}`} className="recent-book-card">
      <div className="recent-cover-wrap">
        <CoverArt book={book} />
      </div>
      <div className="recent-card-copy">
        <div className="chip-row">
          <TagChip>{book.categoryName}</TagChip>
          <TagChip tone="outline">{book.bookFormat}</TagChip>
          <TagChip>{book.readingStatus}</TagChip>
        </div>
        <h4 title={book.title}>{book.title || "タイトル未設定"}</h4>
        <p className="author-line">{book.author || "著者情報なし"}</p>
        <p className="subtle">{formatDate(book.createdAt)}</p>
      </div>
    </Link>
  );
}

export function FloatingScanButton() {
  return (
    <Link to="/scan" className="fab-scan">
      <ScanIcon />
      <span>スキャンする</span>
    </Link>
  );
}

export function CoverArt({
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

export function TagChip({ children, tone = "solid" }: { children: ReactNode; tone?: "solid" | "outline" }) {
  return <span className={`tag-chip ${tone === "outline" ? "is-outline" : ""}`}>{children}</span>;
}

export function SearchIcon() {
  return (
    <svg className="icon search-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M10.5 4a6.5 6.5 0 1 0 4.1 11.54l4.43 4.43 1.41-1.41-4.43-4.43A6.5 6.5 0 0 0 10.5 4Zm0 2a4.5 4.5 0 1 1 0 9 4.5 4.5 0 0 1 0-9Z" fill="currentColor" />
    </svg>
  );
}

export function ScanIcon() {
  return (
    <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 7a3 3 0 0 1 3-3h2v2H7a1 1 0 0 0-1 1v2H4V7Zm13-3h-2v2h2a1 1 0 0 1 1 1v2h2V7a3 3 0 0 0-3-3ZM6 15H4v2a3 3 0 0 0 3 3h2v-2H7a1 1 0 0 1-1-1v-2Zm14 0h-2v2a1 1 0 0 1-1 1h-2v2h2a3 3 0 0 0 3-3v-2ZM7 10h2v4H7v-4Zm4-1h2v6h-2V9Zm4 1h2v4h-2v-4Z" fill="currentColor" />
    </svg>
  );
}

export function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toISOString().slice(0, 10);
}

export function sortBooks<T extends Pick<Book, "createdAt" | "title" | "author">>(
  books: T[],
  sort: "newest" | "oldest" | "title" | "author",
): T[] {
  const next = [...books];
  next.sort((left, right) => {
    if (sort === "oldest") return left.createdAt.localeCompare(right.createdAt);
    if (sort === "title") return left.title.localeCompare(right.title, "ja");
    if (sort === "author") return left.author.localeCompare(right.author, "ja");
    return right.createdAt.localeCompare(left.createdAt);
  });
  return next;
}

export function isInCurrentMonth(value: string): boolean {
  const date = new Date(value);
  const now = new Date();
  return date.getFullYear() === now.getFullYear() && date.getMonth() === now.getMonth();
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
