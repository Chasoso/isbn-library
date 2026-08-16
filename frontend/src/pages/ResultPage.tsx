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
          setMessage("書籍情報の読み込みに失敗しました。");
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
        setMessage("書籍の登録に失敗しました。");
      }
    }
  };

  return (
    <AppLayout title="スキャン結果" subtitle={`ISBN ${isbn}`}>
      <section className={`panel result-banner ${registered ? "is-registered" : "is-unregistered"}`}>
        <p className="section-label">SCAN RESULT</p>
        <h2>
          {loading ? "判定中..." : registered ? "この本はすでに登録されています" : "この本は未登録です"}
        </h2>
        {message ? <p className="subtle">{message}</p> : null}
      </section>

      <section className="panel detail-panel">
        <div className="section-heading">
          <div>
            <p className="section-label">書誌情報</p>
            <h3>登録前に内容を確認します</h3>
          </div>
          {!registered ? (
            <Link className="text-link" to="/categories">
              カテゴリ管理
            </Link>
          ) : null}
        </div>
        {loading ? <p className="empty-copy">書誌情報を取得しています...</p> : null}
        {!loading && lookupFailed ? (
          <p className="empty-copy">外部サービスから書誌情報を取得できませんでした。</p>
        ) : null}
        {!loading && book ? (
          <>
            <div className="detail-grid">
              <CoverArt book={book} large className="detail-cover" />
              <div className="detail-copy">
                <h2>{book.title || "無題"}</h2>
                <dl className="detail-meta-list">
                  <div>
                    <dt>著者</dt>
                    <dd>{book.author || "-"}</dd>
                  </div>
                  <div>
                    <dt>出版社</dt>
                    <dd>{book.publisher || "-"}</dd>
                  </div>
                  <div>
                    <dt>発売日</dt>
                    <dd>{book.publishedDate || "-"}</dd>
                  </div>
                  <div>
                    <dt>形態</dt>
                    <dd>{"bookFormat" in book ? book.bookFormat : bookFormat}</dd>
                  </div>
                  <div>
                    <dt>カテゴリ</dt>
                    <dd>
                      {"categoryName" in book
                        ? book.categoryName
                        : categories.find((item) => item.categoryId === categoryId)?.name ?? "未設定"}
                    </dd>
                  </div>
                  <div>
                    <dt>読書ステータス</dt>
                    <dd>{"readingStatus" in book ? book.readingStatus : readingStatus}</dd>
                  </div>
                </dl>
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
                    {categories.length === 0 ? (
                      <small>先にカテゴリ管理でカテゴリを追加してください。</small>
                    ) : null}
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
                <button className="primary-button" onClick={() => void handleCreate()} disabled={categories.length === 0}>
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
