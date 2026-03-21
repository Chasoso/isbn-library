export const bookFormats = [
  "新書",
  "文庫",
  "単行本",
  "ハードカバー",
  "雑誌",
  "電子書籍",
  "その他",
] as const;

export const defaultCategoryId = "other";

export type BookFormat = (typeof bookFormats)[number];
