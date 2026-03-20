import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { Link } from "react-router-dom";
import type { Book } from "../types";

type CoverFlowShelfProps = {
  books: Book[];
  activeIndex: number;
  onActiveIndexChange: (index: number) => void;
};

type CoverFlowPresentation = {
  rotation: number;
  translateX: number;
  translateZ: number;
  opacity: number;
  zIndex: number;
  mode: "cover" | "spine";
};

const RAIL_ITEM_WIDTH = 220;
const MAX_VISIBLE_OFFSET = 5;

export function CoverFlowShelf({
  books,
  activeIndex,
  onActiveIndexChange,
}: CoverFlowShelfProps) {
  const railRef = useRef<HTMLDivElement | null>(null);
  const railItemRefs = useRef<Array<HTMLDivElement | null>>([]);

  useEffect(() => {
    railItemRefs.current = railItemRefs.current.slice(0, books.length);
  }, [books.length]);

  const visibleBooks = useMemo(
    () =>
      books
        .map((book, index) => ({ book, index, offset: index - activeIndex }))
        .filter(({ offset }) => Math.abs(offset) <= MAX_VISIBLE_OFFSET),
    [books, activeIndex],
  );

  const layeredBooks = useMemo(
    () =>
      [...visibleBooks].sort((left, right) => {
        const leftPresentation = getPresentation(left.offset);
        const rightPresentation = getPresentation(right.offset);
        return leftPresentation.zIndex - rightPresentation.zIndex;
      }),
    [visibleBooks],
  );

  const updateActiveFromScroll = (): void => {
    const rail = railRef.current;
    if (!rail || books.length === 0) {
      return;
    }

    const viewportCenter = rail.scrollLeft + rail.clientWidth / 2;
    let closestIndex = 0;
    let closestDistance = Number.POSITIVE_INFINITY;

    railItemRefs.current.forEach((item, index) => {
      if (!item) {
        return;
      }

      const center = item.offsetLeft + item.offsetWidth / 2;
      const distance = Math.abs(center - viewportCenter);

      if (distance < closestDistance) {
        closestDistance = distance;
        closestIndex = index;
      }
    });

    if (closestIndex !== activeIndex) {
      onActiveIndexChange(closestIndex);
    }
  };

  const focusIndex = (index: number): void => {
    const item = railItemRefs.current[index];
    if (!item) {
      return;
    }

    onActiveIndexChange(index);
    item.scrollIntoView({
      behavior: "smooth",
      inline: "center",
      block: "nearest",
    });
  };

  const selectedBook = books[activeIndex] ?? null;

  return (
    <section className="coverflow-shell">
      <div className="coverflow-stage-wrap">
        <div
          className="coverflow-visual-stage"
          role="region"
          aria-label="蔵書を選択"
        >
          {layeredBooks.map(({ book, index, offset }) => {
            const presentation = getPresentation(offset);
            const origin =
              offset < 0 ? "right center" : offset > 0 ? "left center" : "center center";

            return (
              <button
                key={book.isbn}
                type="button"
                className={`coverflow-book is-${presentation.mode} ${index === activeIndex ? "is-active" : ""}`}
                style={
                  {
                    transform: `translateX(-50%) translateX(${presentation.translateX}px) translateZ(${presentation.translateZ}px) rotateY(${presentation.rotation}deg)`,
                    transformOrigin: origin,
                    opacity: presentation.opacity,
                    zIndex: presentation.zIndex,
                  } as CSSProperties
                }
                onClick={() => focusIndex(index)}
                aria-pressed={index === activeIndex}
                aria-label={`${book.title} を選択`}
              >
                <div className="coverflow-book-inner">
                  {presentation.mode === "spine" ? (
                    <BookSpine book={book} />
                  ) : (
                    <BookSurface book={book} />
                  )}
                </div>
              </button>
            );
          })}
        </div>

        <div ref={railRef} className="coverflow-rail" onScroll={updateActiveFromScroll} aria-hidden="true">
          {books.map((book, index) => (
            <div
              key={book.isbn}
              ref={(node) => {
                railItemRefs.current[index] = node;
              }}
              className="coverflow-rail-stop"
              style={{ width: `${RAIL_ITEM_WIDTH}px` }}
            />
          ))}
        </div>
      </div>

      {selectedBook ? (
        <div className="coverflow-selection">
          <p className="section-label">選択中の本</p>
          <div className="coverflow-selection-main">
            <div>
              <h3>{selectedBook.title}</h3>
              <p>{selectedBook.author || "著者情報なし"}</p>
            </div>
            <div className="chip-row">
              <span className="tag-chip">{selectedBook.readingStatus}</span>
              <span className="tag-chip is-outline">{selectedBook.category}</span>
              <span className="tag-chip is-outline">{selectedBook.bookFormat}</span>
            </div>
          </div>
          <Link to={`/books/${selectedBook.isbn}`} className="ghost-link coverflow-detail-link">
            詳細を見る
          </Link>
        </div>
      ) : null}

      <div className="coverflow-plank" aria-hidden="true" />
    </section>
  );
}

function getPresentation(delta: number): CoverFlowPresentation {
  const direction = delta === 0 ? 0 : delta > 0 ? 1 : -1;
  const distance = Math.abs(delta);

  if (distance === 0) {
    return {
      rotation: 0,
      translateX: 0,
      translateZ: 0,
      opacity: 1,
      zIndex: 70,
      mode: "cover",
    };
  }

  if (distance === 1) {
    return {
      rotation: -46 * direction,
      translateX: 168 * direction,
      translateZ: -80,
      opacity: 0.94,
      zIndex: 56,
      mode: "cover",
    };
  }

  if (distance === 2) {
    return {
      rotation: -72 * direction,
      translateX: 292 * direction,
      translateZ: -150,
      opacity: 0.82,
      zIndex: 42,
      mode: "cover",
    };
  }

  return {
    rotation: -86 * direction,
    translateX: (392 + (distance - 3) * 34) * direction,
    translateZ: -220 - (distance - 3) * 24,
    opacity: Math.max(0.36, 0.56 - (distance - 3) * 0.06),
    zIndex: 24 - distance,
    mode: "spine",
  };
}

function BookSurface({ book }: { book: Book }) {
  const [imageFailed, setImageFailed] = useState(false);

  useEffect(() => {
    setImageFailed(false);
  }, [book.coverImageUrl, book.isbn]);

  if (book.coverImageUrl && !imageFailed) {
    return (
      <div className="coverflow-cover-shell">
        <img
          className="coverflow-cover-image"
          src={book.coverImageUrl}
          alt={book.title || "書影"}
          loading="lazy"
          onError={() => setImageFailed(true)}
        />
      </div>
    );
  }

  return (
    <div
      className="coverflow-cover-shell coverflow-cover-fallback"
      style={{ background: coverFlowAccent(book.isbn) }}
    >
      <span>{book.title || "NO IMAGE"}</span>
    </div>
  );
}

function BookSpine({ book }: { book: Book }) {
  return (
    <div className="coverflow-spine-face" style={{ background: coverFlowAccent(book.isbn) }}>
      <span className="coverflow-spine-title">{book.title || "タイトル未設定"}</span>
      <span className="coverflow-spine-author">{book.author || "著者未設定"}</span>
    </div>
  );
}

function coverFlowAccent(seed: string): string {
  const palettes = [
    "linear-gradient(180deg, #2aa3a7 0%, #14656e 100%)",
    "linear-gradient(180deg, #81c7d4 0%, #4f95ab 100%)",
    "linear-gradient(180deg, #f2c66c 0%, #d38e31 100%)",
    "linear-gradient(180deg, #7fc0a9 0%, #4e8873 100%)",
    "linear-gradient(180deg, #9eb7df 0%, #607fa9 100%)",
  ];
  const score = [...seed].reduce((sum, char) => sum + char.charCodeAt(0), 0);
  return palettes[score % palettes.length];
}
