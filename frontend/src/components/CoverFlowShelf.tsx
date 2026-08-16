import { Link } from "react-router-dom";
import type { Book } from "../types";
import { CoverArt, TagChip } from "../view-helpers";

type CoverFlowShelfProps = {
  books: Book[];
  activeIndex: number;
  onActiveIndexChange: (index: number) => void;
  layout?: "grid" | "list";
};

export function CoverFlowShelf({
  books,
  activeIndex,
  onActiveIndexChange,
  layout = "grid",
}: CoverFlowShelfProps) {
  const selectedBook = books[activeIndex] ?? books[0] ?? null;

  return (
    <section className="bookshelf-shell">
      <div className={`bookshelf-grid ${layout === "list" ? "list-view" : ""}`}>
        {books.map((book, index) => (
          <button
            key={book.isbn}
            type="button"
            className={`bookshelf-book ${index === activeIndex ? "is-selected" : ""}`}
            onClick={() => onActiveIndexChange(index)}
            aria-pressed={index === activeIndex}
            aria-label={`${book.title} select`}
          >
            <CoverArt book={book} className="bookshelf-cover" />
            <div className="bookshelf-copy">
              <div className="chip-row">
                <TagChip>{book.readingStatus}</TagChip>
                <TagChip tone="outline">{book.bookFormat}</TagChip>
              </div>
              <h4>{book.title || "Untitled"}</h4>
              <p>{book.author || "Unknown author"}</p>
              <small>{book.categoryName}</small>
            </div>
          </button>
        ))}
      </div>

      {selectedBook ? (
        <div className="bookshelf-selection">
          <div className="section-heading">
            <div>
              <p className="section-label">Selected book</p>
              <h3>{selectedBook.title}</h3>
            </div>
            <Link to={`/books/${selectedBook.isbn}`} className="text-link">
              Open detail
            </Link>
          </div>
          <div className="bookshelf-selection-main">
            <CoverArt book={selectedBook} large />
            <div className="bookshelf-selection-copy">
              <div className="chip-row">
                <TagChip>{selectedBook.categoryName}</TagChip>
                <TagChip tone="outline">{selectedBook.bookFormat}</TagChip>
                <TagChip>{selectedBook.readingStatus}</TagChip>
              </div>
              <p className="subtle">{selectedBook.author || "Unknown author"}</p>
              <p>{selectedBook.publisher || "-"}</p>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
