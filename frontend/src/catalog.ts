export const bookFormats = [
  "新書",
  "文庫",
  "単行本",
  "ハードカバー",
  "雑誌",
  "電子書籍",
  "その他",
] as const;

export const categories = [
  "技術書",
  "小説",
  "ビジネス",
  "デザイン",
  "歴史",
  "統計",
  "趣味",
  "漫画",
  "その他",
] as const;

export type BookFormat = (typeof bookFormats)[number];
export type Category = (typeof categories)[number];
