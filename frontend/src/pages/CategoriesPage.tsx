import { useEffect, useState } from "react";
import { AppLayout } from "../app-shell";
import { ApiError, createCategory, getCategories, updateCategory } from "../lib/api";
import type { CategoryDefinition } from "../types";

export function CategoriesPage({ accessToken }: { accessToken: string }) {
  const [categories, setCategories] = useState<CategoryDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState("");
  const [newNameEn, setNewNameEn] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const loadCategories = async (): Promise<void> => {
    setLoading(true);
    try {
      const result = await getCategories(accessToken);
      setCategories(result.items);
    } catch {
      setMessage("カテゴリ一覧の取得に失敗しました。");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadCategories();
  }, [accessToken]);

  const handleCreate = async (): Promise<void> => {
    if (!newName.trim()) return;

    setSaving(true);
    setMessage(null);
    try {
      const created = await createCategory(accessToken, {
        name: newName.trim(),
        nameEn: newNameEn.trim(),
      });
      setCategories((prev) =>
        [...prev, created].sort((left, right) => left.sortOrder - right.sortOrder),
      );
      setNewName("");
      setNewNameEn("");
      setMessage("カテゴリを追加しました。");
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setMessage("同じ名前のカテゴリがすでに存在します。");
      } else {
        setMessage("カテゴリの追加に失敗しました。");
      }
    } finally {
      setSaving(false);
    }
  };

  const handleRename = async (categoryId: string, name: string, nameEn: string): Promise<void> => {
    const trimmed = name.trim();
    if (!trimmed) return;

    try {
      const updated = await updateCategory(accessToken, categoryId, {
        name: trimmed,
        nameEn: nameEn.trim(),
      });
      setCategories((prev) =>
        prev
          .map((item) => (item.categoryId === categoryId ? updated : item))
          .sort((left, right) => left.sortOrder - right.sortOrder),
      );
      setMessage("カテゴリ名を更新しました。");
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setMessage("同じ名前のカテゴリがすでに存在します。");
      } else {
        setMessage("カテゴリの更新に失敗しました。");
      }
    }
  };

  return (
    <AppLayout title="カテゴリ管理" subtitle="蔵書の分類を自由に整える">
      <section className="panel category-settings">
        <div className="section-heading">
          <div>
            <p className="section-label">カテゴリマスタ</p>
            <h3>カテゴリを追加・編集する</h3>
          </div>
        </div>
        {message ? <p className="subtle">{message}</p> : null}
        <div className="category-create-row">
          <input
            value={newName}
            onChange={(event) => setNewName(event.target.value)}
            placeholder="新しいカテゴリ名"
            aria-label="新しいカテゴリ名"
          />
          <input
            value={newNameEn}
            onChange={(event) => setNewNameEn(event.target.value)}
            placeholder="English category name"
            aria-label="English category name"
          />
          <button className="primary-pill" onClick={() => void handleCreate()} disabled={saving}>
            追加
          </button>
        </div>
        {loading ? <p className="empty-copy">カテゴリを読み込み中です...</p> : null}
        {!loading ? (
          <div className="category-list">
            {categories.map((category) => (
              <CategoryRow
                key={category.categoryId}
                category={category}
                onSave={handleRename}
              />
            ))}
          </div>
        ) : null}
      </section>
    </AppLayout>
  );
}

function CategoryRow({
  category,
  onSave,
}: {
  category: CategoryDefinition;
  onSave: (categoryId: string, name: string, nameEn: string) => Promise<void>;
}) {
  const [name, setName] = useState(category.name);
  const [nameEn, setNameEn] = useState(category.nameEn ?? "");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setName(category.name);
    setNameEn(category.nameEn ?? "");
  }, [category.name, category.nameEn]);

  return (
    <div className="category-card">
      <div className="category-card-meta">
        <span className="section-label">#{category.sortOrder}</span>
        <strong>{category.name}</strong>
        {category.nameEn ? <span className="subtle">{category.nameEn}</span> : null}
      </div>
      <div className="category-card-editor">
        <input
          value={name}
          onChange={(event) => setName(event.target.value)}
          aria-label={`${category.name} の日本語名`}
        />
        <input
          value={nameEn}
          onChange={(event) => setNameEn(event.target.value)}
          aria-label={`${category.name} の英語名`}
          placeholder="English name"
        />
        <button
          className="secondary-pill"
          onClick={() => {
            setSaving(true);
            void onSave(category.categoryId, name, nameEn).finally(() => setSaving(false));
          }}
          disabled={saving}
        >
          保存
        </button>
      </div>
    </div>
  );
}
