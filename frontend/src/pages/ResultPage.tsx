import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { defaultCategoryId, bookFormats, type BookFormat } from "../catalog";
import { AppLayout } from "../app-shell";
import { ApiError, createBook, getBook, getCategories, lookupBook } from "../lib/api";
import { readingStatuses, type ReadingStatus } from "../readingStatus";
import type { Book, BookLookupResult, CategoryDefinition } from "../types";
import { CoverArt } from "../view-helpers";

const defaultBookFormat: BookFormat = bookFormats[bookFormats.length - 1];
const defaultReadingStatus: ReadingStatus = readingStatuses[0];

export function ResultPage({ accessToken }: { accessToken: string }) {
  const { isbn = "" } = useParams();
  const navigate = useNavigate();
  const [book, setBook] = useState<BookLookupResult | Book | null>(null);
  const [registered, setRegistered] = useState(false);
  const [lookupFailed, setLookupFailed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [categories, setCategories] = useState<CategoryDefinition[]>([]);
  const [bookFormat, setBookFormat] = useState<BookFormat>(defaultBookFormat);
  const [categoryId, setCategoryId] = useState(defaultCategoryId);
  const [readingStatus, setReadingStatus] = useState<ReadingStatus>(defaultReadingStatus);

  useEffect(() => {
    const loadCategories = async (): Promise<void> => {
      try {
        const result = await getCategories(accessToken);
        setCategories(result.items);
        if (result.items.length > 0) {
          setCategoryId(result.items[0].categoryId);
        }
      } catch {
        setCategories([]);
      }
    };

    void loadCategories();
  }, [accessToken]);

  useEffect(() => {
    const load = async (): Promise<void> => {
      setLoading(true);
      setLookupFailed(false);
      setMessage(null);

      try {
        const existing = await getBook(accessToken, isbn);
        setRegistered(true);
        setBook(existing);
      } catch (error) {
        if (!(error instanceof ApiError) || error.status !== 404) {
          setMessage("書籍情報の取得に失敗しました。");
          setLoading(false);
          return;
        }

        setRegistered(false);

        try {
          const lookedUp = await lookupBook(accessToken, isbn);
          setBook(lookedUp);
        } catch (lookupError) {
          if (lookupError instanceof ApiError && lookupError.status === 404) {
            setLookupFailed(true);
            setBook(null);
          } else if (lookupError instanceof ApiError && lookupError.status === 503) {
            setMessage("書誌情報の取得が混み合っています。少し待ってから再試行してください。");
          } else {
            setMessage("書誌情報の取得に失敗しました。");
          }
        }
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, [accessToken, isbn]);

  const handleCreate = async (): Promise<void> => {
    if (!book || registered) return;

    try {
      await createBook(accessToken, {
        isbn,
        title: book.title,
        author: book.author,
        publisher: book.publisher,
        publishedDate: book.publishedDate,
        coverImageUrl: book.coverImageUrl,
        bookFormat,
        categoryId,
        readingStatus,
      });
      navigate(`/books/${isbn}`, { replace: true });
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setRegistered(true);
        setMessage("この本はすでに登録されています。");
      } else {
        setMessage("登録に失敗しました。");
      }
    }
  };

  return (
    <AppLayout title="判定結果" subtitle={`ISBN ${isbn}`}>
      <section className={`panel result-banner ${registered ? "is-registered" : "is-unregistered"}`}>
        <p className="section-label">判定ステータス</p>
        <h2>
          {loading
            ? "判定中..."
            : registered
              ? "この本はすでに登録されています"
              : "この本は未登録です"}
        </h2>
        {message ? <p className="subtle">{message}</p> : null}
      </section>

      <section className="panel detail-panel">
        <div className="section-heading">
          <div>
            <p className="section-label">書誌情報</p>
            <h3>登録前に内容を確認</h3>
          </div>
          {!registered ? (
            <Link className="text-link" to="/categories">
              カテゴリ管理
            </Link>
          ) : null}
        </div>
        {loading ? <p className="empty-copy">書誌情報を取得しています...</p> : null}
        {!loading && lookupFailed ? (
          <p className="empty-copy">Google Books API から書誌情報を取得できませんでした。</p>
        ) : null}
        {!loading && book ? (
          <>
            <div className="detail-grid">
              <CoverArt book={book} large />
              <div className="detail-copy">
                <h2>{book.title || "タイトル未設定"}</h2>
                <p><strong>著者:</strong> {book.author || "-"}</p>
                <p><strong>出版社:</strong> {book.publisher || "-"}</p>
                <p><strong>発売日:</strong> {book.publishedDate || "-"}</p>
                <p><strong>分類:</strong> {"bookFormat" in book ? book.bookFormat : bookFormat}</p>
                <p>
                  <strong>カテゴリ:</strong>{" "}
                  {"categoryName" in book
                    ? book.categoryName
                    : categories.find((item) => item.categoryId === categoryId)?.name ?? "その他"}
                </p>
                <p><strong>読書ステータス:</strong> {"readingStatus" in book ? book.readingStatus : readingStatus}</p>
              </div>
            </div>
            {!registered ? (
              <>
                <div className="classification-grid">
                  <label>
                    <span>形態</span>
                    <select
                      value={bookFormat}
                      onChange={(event) => setBookFormat(event.target.value as BookFormat)}
                    >
                      {bookFormats.map((item) => (
                        <option key={item} value={item}>
                          {item}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span>カテゴリ</span>
                    <select value={categoryId} onChange={(event) => setCategoryId(event.target.value)}>
                      {categories.map((item) => (
                        <option key={item.categoryId} value={item.categoryId}>
                          {item.name}
                        </option>
                      ))}
                    </select>
                    {categories.length === 0 ? <small>カテゴリ管理で先にカテゴリを作成してください。</small> : null}
                  </label>
                  <label>
                    <span>読書ステータス</span>
                    <select
                      value={readingStatus}
                      onChange={(event) => setReadingStatus(event.target.value as ReadingStatus)}
                    >
                      {readingStatuses.map((item) => (
                        <option key={item} value={item}>
                          {item}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
                <button className="primary-pill" onClick={() => void handleCreate()} disabled={categories.length === 0}>
                  蔵書に登録する
                </button>
              </>
            ) : null}
          </>
        ) : null}
      </section>
    </AppLayout>
  );
}
