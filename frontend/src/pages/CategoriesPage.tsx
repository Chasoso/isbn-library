import { useEffect, useMemo, useState } from "react";
import { AppLayout } from "../app-shell";
import { ApiError, createCategory, getBooks, getCategories, updateCategory } from "../lib/api";
import type { Book, CategoryDefinition } from "../types";

type EditorState =
  | {
      mode: "create";
      categoryId: null;
      name: string;
      nameEn: string;
    }
  | {
      mode: "edit";
      categoryId: string;
      name: string;
      nameEn: string;
    };

export function CategoriesPage({ accessToken }: { accessToken: string }) {
  const [categories, setCategories] = useState<CategoryDefinition[]>([]);
  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [editor, setEditor] = useState<EditorState | null>(null);

  useEffect(() => {
    const load = async (): Promise<void> => {
      setLoading(true);
      try {
        const [categoryResult, bookResult] = await Promise.all([getCategories(accessToken), getBooks(accessToken)]);
        setCategories(categoryResult.items);
        setBooks(bookResult.items);
      } catch {
        setMessage("カテゴリの読み込みに失敗しました。");
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, [accessToken]);

  const bookCountByCategory = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const book of books) {
      counts[book.categoryId] = (counts[book.categoryId] ?? 0) + 1;
    }
    return counts;
  }, [books]);

  const filteredCategories = useMemo(() => {
    const query = search.trim().toLowerCase();
    return [...categories]
      .filter((category) => {
        if (!query) return true;
        return `${category.name}${category.nameEn ?? ""}`.toLowerCase().includes(query);
      })
      .sort((left, right) => left.sortOrder - right.sortOrder);
  }, [categories, search]);

  const openCreate = (): void => {
    setEditor({
      mode: "create",
      categoryId: null,
      name: "",
      nameEn: "",
    });
  };

  const openEdit = (category: CategoryDefinition): void => {
    setEditor({
      mode: "edit",
      categoryId: category.categoryId,
      name: category.name,
      nameEn: category.nameEn ?? "",
    });
  };

  const saveEditor = async (): Promise<void> => {
    if (!editor || !editor.name.trim()) {
      return;
    }

    setSaving(true);
    setMessage(null);

    try {
      if (editor.mode === "create") {
        const created = await createCategory(accessToken, {
          name: editor.name.trim(),
          nameEn: editor.nameEn.trim(),
        });
        setCategories((current) => [...current, created].sort((left, right) => left.sortOrder - right.sortOrder));
        setMessage("カテゴリを追加しました。");
      } else {
        const updated = await updateCategory(accessToken, editor.categoryId, {
          name: editor.name.trim(),
          nameEn: editor.nameEn.trim(),
        });
        setCategories((current) =>
          current
            .map((category) => (category.categoryId === editor.categoryId ? updated : category))
            .sort((left, right) => left.sortOrder - right.sortOrder),
        );
        setMessage("カテゴリを更新しました。");
      }

      setEditor(null);
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setMessage("同じ名前のカテゴリがすでにあります。");
      } else {
        setMessage("カテゴリの保存に失敗しました。");
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <AppLayout title="カテゴリ管理" subtitle="棚のラベルを整えて、分類を見やすくします。">
      <section className="panel categories-panel">
        <div className="section-heading category-heading">
          <div>
            <p className="section-label">CATEGORY LIST</p>
            <h3>カテゴリを編集する</h3>
          </div>
          <button className="primary-button" type="button" onClick={openCreate}>
            ＋ 追加
          </button>
        </div>

        <div className="category-toolbar">
          <div className="category-search">
            <span aria-hidden="true">⌕</span>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="カテゴリを検索"
              aria-label="カテゴリを検索"
            />
          </div>
          <p className="subtle category-summary">{filteredCategories.length}件</p>
        </div>

        {message ? <p className="subtle">{message}</p> : null}
        {loading ? <p className="empty-copy">カテゴリを読み込み中です...</p> : null}

        {!loading ? (
          <div className="category-table">
            <div className="category-table-head">
              <span>日本語名</span>
              <span>英語名</span>
              <span>冊数</span>
              <span>操作</span>
            </div>
            {filteredCategories.length > 0 ? (
              filteredCategories.map((category) => (
                <div className="category-row" key={category.categoryId}>
                  <div className="category-row-main">
                    <strong>{category.name}</strong>
                    <small>{category.nameEn || " "}</small>
                  </div>
                  <span className="category-row-english">{category.nameEn || "-"}</span>
                  <span className="book-count">{bookCountByCategory[category.categoryId] ?? 0}</span>
                  <button
                    type="button"
                    className="row-action"
                    onClick={() => openEdit(category)}
                    aria-label={`${category.name} を編集`}
                  >
                    …
                  </button>
                </div>
              ))
            ) : (
              <div className="empty-state">
                <h4>カテゴリが見つかりませんでした</h4>
                <p>検索条件を変えるか、新しいカテゴリを追加してください。</p>
              </div>
            )}
          </div>
        ) : null}
      </section>

      {editor ? (
        <div className="modal-backdrop" onMouseDown={() => setEditor(null)}>
          <section
            className="edit-sheet"
            role="dialog"
            aria-modal="true"
            aria-labelledby="category-editor-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="sheet-heading">
              <div>
                <p className="eyebrow">{editor.mode === "create" ? "NEW CATEGORY" : "EDIT CATEGORY"}</p>
                <h2 id="category-editor-title">{editor.mode === "create" ? "カテゴリを追加" : "カテゴリを編集"}</h2>
              </div>
              <button type="button" className="icon-button" onClick={() => setEditor(null)} aria-label="閉じる">
                ×
              </button>
            </div>
            <label>
              日本語名
              <input
                value={editor.name}
                onChange={(event) => setEditor({ ...editor, name: event.target.value })}
                placeholder="カテゴリ名"
                aria-label="日本語名"
              />
            </label>
            <label>
              英語名
              <input
                value={editor.nameEn}
                onChange={(event) => setEditor({ ...editor, nameEn: event.target.value })}
                placeholder="English name"
                aria-label="英語名"
              />
            </label>
            <div className="sheet-actions">
              <button type="button" className="ghost-button" onClick={() => setEditor(null)}>
                キャンセル
              </button>
              <button
                type="button"
                className="primary-button"
                onClick={() => void saveEditor()}
                disabled={saving || !editor.name.trim()}
              >
                {saving ? "保存中..." : "保存"}
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </AppLayout>
  );
}
