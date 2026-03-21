import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { AppLayout } from "../app-shell";
import { ApiError, deleteBook, getBook, updateBookStatus } from "../lib/api";
import { readingStatuses, type ReadingStatus } from "../readingStatus";
import type { Book } from "../types";
import { CoverArt, TagChip, formatDate } from "../view-helpers";

const defaultReadingStatus: ReadingStatus = readingStatuses[0];

export function BookDetailPage({ accessToken }: { accessToken: string }) {
  const { isbn = "" } = useParams();
  const navigate = useNavigate();
  const [book, setBook] = useState<Book | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [readingStatus, setReadingStatus] = useState<ReadingStatus>(defaultReadingStatus);
  const [savingStatus, setSavingStatus] = useState(false);

  useEffect(() => {
    const load = async (): Promise<void> => {
      try {
        const result = await getBook(accessToken, isbn);
        setBook(result);
        setReadingStatus(result.readingStatus);
        setNotFound(false);
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) {
          setNotFound(true);
          setMessage("対象の書籍は登録されていません。");
        } else {
          setMessage("書籍情報の取得に失敗しました。");
        }
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, [accessToken, isbn]);

  const handleDelete = async (): Promise<void> => {
    if (!window.confirm("この書籍を蔵書から削除しますか？")) {
      return;
    }

    try {
      await deleteBook(accessToken, isbn);
      navigate("/books", { replace: true });
    } catch {
      setMessage("削除に失敗しました。");
    }
  };

  const handleUpdateReadingStatus = async (): Promise<void> => {
    if (!book) return;

    setSavingStatus(true);
    setMessage(null);
    try {
      const updated = await updateBookStatus(accessToken, isbn, readingStatus);
      setBook(updated);
      setReadingStatus(updated.readingStatus);
      setMessage("読書ステータスを更新しました。");
    } catch {
      setMessage("読書ステータスの更新に失敗しました。");
    } finally {
      setSavingStatus(false);
    }
  };

  return (
    <AppLayout title="書籍詳細" subtitle={book?.title ?? "書籍の詳細を確認"}>
      <section className="panel detail-panel">
        {loading ? <p className="empty-copy">書籍情報を読み込み中です...</p> : null}
        {message ? <p className="subtle">{message}</p> : null}
        {notFound ? (
          <p>
            <Link className="text-link" to="/books">蔵書一覧へ戻る</Link>
          </p>
        ) : null}
        {book ? (
          <>
            <div className="detail-grid">
              <CoverArt book={book} large />
              <div className="detail-copy">
                <div className="chip-row">
                  <TagChip>{book.categoryName}</TagChip>
                  <TagChip tone="outline">{book.bookFormat}</TagChip>
                  <TagChip>{book.readingStatus}</TagChip>
                </div>
                <h2>{book.title}</h2>
                <p><strong>著者:</strong> {book.author || "-"}</p>
                <p><strong>出版社:</strong> {book.publisher || "-"}</p>
                <p><strong>発売日:</strong> {book.publishedDate || "-"}</p>
                <p><strong>ISBN:</strong> {book.isbn}</p>
                <p><strong>読書ステータス:</strong> {book.readingStatus}</p>
                <p><strong>登録日:</strong> {formatDate(book.createdAt)}</p>
              </div>
            </div>
            <div className="detail-status-panel">
              <div className="classification-grid detail-status-grid">
                <label>
                  <span>読書ステータス</span>
                  <select
                    value={readingStatus}
                    onChange={(event) => setReadingStatus(event.target.value as ReadingStatus)}
                    disabled={savingStatus}
                  >
                    {readingStatuses.map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="detail-actions">
                <button className="primary-pill" onClick={() => void handleUpdateReadingStatus()} disabled={savingStatus}>
                  {savingStatus ? "保存中..." : "ステータスを保存"}
                </button>
                <button className="danger-pill" onClick={() => void handleDelete()}>
                  削除する
                </button>
              </div>
            </div>
          </>
        ) : null}
      </section>
    </AppLayout>
  );
}
