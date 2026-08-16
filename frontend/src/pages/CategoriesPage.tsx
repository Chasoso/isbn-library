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
        const [categoryResult, bookResult] = await Promise.all([
          getCategories(accessToken),
          getBooks(accessToken),
        ]);
        setCategories(categoryResult.items);
        setBooks(bookResult.items);
      } catch {
        setMessage("Failed to load categories.");
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
        setCategories((current) =>
          [...current, created].sort((left, right) => left.sortOrder - right.sortOrder),
        );
        setMessage("Category created.");
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
        setMessage("Category updated.");
      }

      setEditor(null);
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setMessage("A category with the same name already exists.");
      } else {
        setMessage("Failed to save category.");
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <AppLayout title="Categories" subtitle="Keep the shelf taxonomy compact and editable.">
      <section className="panel categories-panel">
        <div className="section-heading">
          <div>
            <p className="section-label">CATEGORY LIST</p>
            <h3>Manage the labels behind the shelf</h3>
          </div>
          <button className="primary-button" type="button" onClick={openCreate}>
            Add category
          </button>
        </div>

        <div className="category-toolbar">
          <div className="category-search">
            <span aria-hidden="true">⌕</span>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search categories"
              aria-label="Search categories"
            />
          </div>
          <p className="subtle category-summary">
            {filteredCategories.length} categories
          </p>
        </div>

        {message ? <p className="subtle">{message}</p> : null}
        {loading ? <p className="empty-copy">Loading categories...</p> : null}

        {!loading ? (
          <div className="category-table">
            <div className="category-table-head">
              <span>Japanese</span>
              <span>English</span>
              <span>Books</span>
              <span>Action</span>
            </div>
            {filteredCategories.length > 0 ? (
              filteredCategories.map((category) => (
                <div className="category-row" key={category.categoryId}>
                  <div className="category-row-main">
                    <strong>{category.name}</strong>
                    <small>#{category.sortOrder}</small>
                  </div>
                  <span className="category-row-english">{category.nameEn || "-"}</span>
                  <span className="book-count">{bookCountByCategory[category.categoryId] ?? 0}</span>
                  <button
                    type="button"
                    className="row-action"
                    onClick={() => openEdit(category)}
                    aria-label={`Edit ${category.name}`}
                  >
                    Edit
                  </button>
                </div>
              ))
            ) : (
              <div className="empty-state">
                <h4>No categories found</h4>
                <p>Try a different search term or add a new category.</p>
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
                <h2 id="category-editor-title">
                  {editor.mode === "create" ? "Add a category" : "Update category"}
                </h2>
              </div>
              <button type="button" className="icon-button" onClick={() => setEditor(null)} aria-label="Close editor">
                ×
              </button>
            </div>
            <label>
              Japanese name
              <input
                value={editor.name}
                onChange={(event) => setEditor({ ...editor, name: event.target.value })}
                placeholder="Category name"
                aria-label="Japanese name"
              />
            </label>
            <label>
              English name
              <input
                value={editor.nameEn}
                onChange={(event) => setEditor({ ...editor, nameEn: event.target.value })}
                placeholder="English name"
                aria-label="English name"
              />
            </label>
            <div className="sheet-actions">
              <button type="button" className="ghost-button" onClick={() => setEditor(null)}>
                Cancel
              </button>
              <button
                type="button"
                className="primary-button"
                onClick={() => void saveEditor()}
                disabled={saving || !editor.name.trim()}
              >
                {saving ? "Saving..." : "Save"}
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </AppLayout>
  );
}
