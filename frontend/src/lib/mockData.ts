import { defaultCategoryId } from "../catalog";
import type {
  Book,
  BookLookupResult,
  CategoryDefinition,
  CreateBookPayload,
  CreateCategoryPayload,
  UpdateCategoryPayload,
} from "../types";

const createMockCover = (title: string, accent: string, subtitle: string): string => {
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="480" height="720" viewBox="0 0 480 720">
      <defs>
        <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="${accent}" />
          <stop offset="100%" stop-color="#173042" />
        </linearGradient>
      </defs>
      <rect width="480" height="720" rx="28" fill="url(#bg)" />
      <rect x="28" y="28" width="14" height="664" rx="7" fill="rgba(255,255,255,0.7)" />
      <text x="64" y="120" fill="white" font-size="26" font-family="Arial, sans-serif">${subtitle}</text>
      <foreignObject x="64" y="150" width="360" height="420">
        <div xmlns="http://www.w3.org/1999/xhtml" style="color:white;font-size:44px;font-weight:700;line-height:1.2;font-family:Arial,sans-serif;">
          ${title}
        </div>
      </foreignObject>
    </svg>
  `;

  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
};

const demoCategories: CategoryDefinition[] = [
  {
    categoryId: "technology",
    name: "技術書",
    sortOrder: 10,
    color: "#4C8BF5",
    createdAt: "2026-03-20T10:00:00Z",
    updatedAt: "2026-03-20T10:00:00Z",
  },
  {
    categoryId: "business",
    name: "ビジネス",
    sortOrder: 20,
    color: "#35A271",
    createdAt: "2026-03-20T10:00:00Z",
    updatedAt: "2026-03-20T10:00:00Z",
  },
  {
    categoryId: defaultCategoryId,
    name: "その他",
    sortOrder: 90,
    color: "#8FA2B6",
    createdAt: "2026-03-20T10:00:00Z",
    updatedAt: "2026-03-20T10:00:00Z",
  },
];

const categoryName = (categoryId: string): string =>
  memoryCategories.find((item) => item.categoryId === categoryId)?.name ?? "その他";

const demoBooks: Book[] = [
  {
    userId: "demo-user",
    isbn: "9784860648114",
    title: "ネイティブが日常会話でよく使っている感じがいい英語フレーズ大全",
    author: "Blake Turnbull",
    publisher: "ベレ出版",
    publishedDate: "2024-03-12",
    coverImageUrl: createMockCover("英語フレーズ大全", "#35b6b0", "ビジネス"),
    bookFormat: "単行本",
    categoryId: "business",
    categoryName: "ビジネス",
    readingStatus: "読書中",
    createdAt: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
  },
  {
    userId: "demo-user",
    isbn: "9784798183251",
    title: "優れたエンジニアがコミュニティの中でしていること",
    author: "黒須 義一, 酒井 真弓, 宮本 佳歩",
    publisher: "翔泳社",
    publishedDate: "2025-01-20",
    coverImageUrl: createMockCover("コミュニティの中でしていること", "#f0b24f", "技術書"),
    bookFormat: "単行本",
    categoryId: "technology",
    categoryName: "技術書",
    readingStatus: "未読",
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
  },
  {
    userId: "demo-user",
    isbn: "9784295018599",
    title: "Atomic Habits",
    author: "James Clear",
    publisher: "パンローリング",
    publishedDate: "2022-11-02",
    coverImageUrl: createMockCover("Atomic Habits", "#7ab7cf", "その他"),
    bookFormat: "ハードカバー",
    categoryId: defaultCategoryId,
    categoryName: "その他",
    readingStatus: "完了",
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 26).toISOString(),
  },
];

let memoryBooks = [...demoBooks];
let memoryCategories = [...demoCategories];

const matchesQuery = (book: Book, query?: string): boolean => {
  if (!query) return true;
  const normalized = query.trim().toLowerCase();
  if (!normalized) return true;
  return (
    book.title.toLowerCase().includes(normalized) ||
    book.author.toLowerCase().includes(normalized)
  );
};

export const mockSession = {
  getBooks(filters?: {
    query?: string;
    bookFormat?: string;
    categoryId?: string;
    readingStatus?: string;
  }): { items: Book[] } {
    return {
      items: memoryBooks.filter(
        (book) =>
          matchesQuery(book, filters?.query) &&
          (!filters?.bookFormat || book.bookFormat === filters.bookFormat) &&
          (!filters?.categoryId || book.categoryId === filters.categoryId) &&
          (!filters?.readingStatus || book.readingStatus === filters.readingStatus),
      ),
    };
  },
  getBook(isbn: string): Book {
    const book = memoryBooks.find((item) => item.isbn === isbn);
    if (!book) {
      throw new Error("Book not found");
    }
    return book;
  },
  getCategories(): { items: CategoryDefinition[] } {
    return { items: [...memoryCategories].sort((left, right) => left.sortOrder - right.sortOrder) };
  },
  lookupBook(isbn: string): BookLookupResult {
    const existing = memoryBooks.find((item) => item.isbn === isbn);
    if (existing) {
      return {
        isbn: existing.isbn,
        title: existing.title,
        author: existing.author,
        publisher: existing.publisher,
        publishedDate: existing.publishedDate,
        coverImageUrl: existing.coverImageUrl,
      };
    }

    return {
      isbn,
      title: "新しく見つかった本",
      author: "デモ著者",
      publisher: "デモ出版社",
      publishedDate: "2026-03-01",
      coverImageUrl: createMockCover("新しく見つかった本", "#9ab7da", "その他"),
    };
  },
  createBook(payload: CreateBookPayload): Book {
    const duplicate = memoryBooks.find((item) => item.isbn === payload.isbn);
    if (duplicate) {
      throw new Error("Book already exists");
    }

    const created: Book = {
      userId: "demo-user",
      createdAt: new Date().toISOString(),
      categoryName: categoryName(payload.categoryId),
      ...payload,
    };

    memoryBooks = [created, ...memoryBooks];
    return created;
  },
  createCategory(payload: CreateCategoryPayload): CategoryDefinition {
    const name = payload.name.trim();
    if (!name) {
      throw new Error("Category name is required");
    }
    const created: CategoryDefinition = {
      categoryId: `cat_${memoryCategories.length + 1}`,
      name,
      color: payload.color ?? "",
      sortOrder:
        Math.max(...memoryCategories.map((item) => item.sortOrder), 0) + 10,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    memoryCategories = [...memoryCategories, created];
    return created;
  },
  updateCategory(categoryId: string, payload: UpdateCategoryPayload): CategoryDefinition {
    const category = memoryCategories.find((item) => item.categoryId === categoryId);
    if (!category) {
      throw new Error("Category not found");
    }
    if (payload.name !== undefined) {
      category.name = payload.name.trim() || category.name;
      memoryBooks = memoryBooks.map((book) =>
        book.categoryId === categoryId ? { ...book, categoryName: category.name } : book,
      );
    }
    if (payload.color !== undefined) {
      category.color = payload.color;
    }
    if (payload.sortOrder !== undefined) {
      category.sortOrder = payload.sortOrder;
    }
    category.updatedAt = new Date().toISOString();
    return category;
  },
  updateBookStatus(isbn: string, readingStatus: string): Book {
    const book = memoryBooks.find((item) => item.isbn === isbn);
    if (!book) {
      throw new Error("Book not found");
    }
    book.readingStatus = readingStatus as Book["readingStatus"];
    return book;
  },
  deleteBook(isbn: string): void {
    memoryBooks = memoryBooks.filter((item) => item.isbn !== isbn);
  },
  reset(): void {
    memoryBooks = [...demoBooks];
    memoryCategories = [...demoCategories];
  },
};
