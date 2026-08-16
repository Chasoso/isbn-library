import { Link } from "react-router-dom";
import type { Book } from "../types";
import { CoverArt, TagChip } from "../view-helpers";

type CoverFlowShelfProps = {
  books: Book[];
  layout?: "grid" | "list";
};

export function CoverFlowShelf({ books, layout = "grid" }: CoverFlowShelfProps) {
  return (
    <section className="bookshelf-shell">
      <div className={`bookshelf-grid ${layout === "list" ? "list-view" : "grid-view"}`}>
        {books.map((book) => (
          <Link
            key={book.isbn}
            to={`/books/${book.isbn}`}
            className={`bookshelf-book ${layout === "list" ? "bookshelf-book-list" : "bookshelf-book-grid"}`}
            aria-label={`${book.title} の詳細を見る`}
          >
            <CoverArt book={book} className="bookshelf-cover" />
            <div className="bookshelf-copy">
              <div className="chip-row">
                <TagChip>{book.readingStatus}</TagChip>
                <TagChip tone="outline">{book.bookFormat}</TagChip>
              </div>
              <h4 title={book.title}>{book.title || "無題"}</h4>
              <p>{book.author || "著者未設定"}</p>
              <small>{book.categoryName}</small>
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}
