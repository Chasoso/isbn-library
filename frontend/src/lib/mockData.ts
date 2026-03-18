import type { Book, BookLookupResult, CreateBookPayload } from "../types";

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
    category: "ビジネス",
    createdAt: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
  },
  {
    userId: "demo-user",
    isbn: "9784798183251",
    title: "優れたエンジニアがコミュニティの中でしていること",
    author: "黒須 善一, 酒井 真弓, 宮本 佳歩",
    publisher: "翔泳社",
    publishedDate: "2025-01-20",
    coverImageUrl: createMockCover("コミュニティの中でしていること", "#f0b24f", "技術書"),
    bookFormat: "単行本",
    category: "技術書",
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
  },
  {
    userId: "demo-user",
    isbn: "9784295018599",
    title: "Atomic Habits",
    author: "James Clear",
    publisher: "パンローリング",
    publishedDate: "2022-11-02",
    coverImageUrl: createMockCover("Atomic Habits", "#7ab7cf", "趣味"),
    bookFormat: "ハードカバー",
    category: "趣味",
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 26).toISOString(),
  },
  {
    userId: "demo-user",
    isbn: "9784296116904",
    title: "10年後、後悔しないための読書術",
    author: "藤木 俊明",
    publisher: "日経BP",
    publishedDate: "2023-07-01",
    coverImageUrl: createMockCover("10年後、後悔しないための読書術", "#90c98c", "ビジネス"),
    bookFormat: "新書",
    category: "ビジネス",
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 48).toISOString(),
  },
  {
    userId: "demo-user",
    isbn: "9784815615758",
    title: "統計学が最強の学問である",
    author: "西内 啓",
    publisher: "ダイヤモンド社",
    publishedDate: "2024-10-10",
    coverImageUrl: createMockCover("統計学が最強の学問である", "#708ed6", "統計"),
    bookFormat: "文庫",
    category: "統計",
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 72).toISOString(),
  },
  {
    userId: "demo-user",
    isbn: "9784478116692",
    title: "復習する技術",
    author: "山崎 良",
    publisher: "ダイヤモンド社",
    publishedDate: "2023-12-01",
    coverImageUrl: createMockCover("復習する技術", "#3a8db0", "技術書"),
    bookFormat: "新書",
    category: "技術書",
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 96).toISOString(),
  },
];

let memoryBooks = [...demoBooks];

const matchesQuery = (book: Book, query?: string): boolean => {
  if (!query) {
    return true;
  }

  const normalized = query.trim().toLowerCase();
  if (!normalized) {
    return true;
  }

  return (
    book.title.toLowerCase().includes(normalized) ||
    book.author.toLowerCase().includes(normalized)
  );
};

export const mockSession = {
  getBooks(filters?: { query?: string; bookFormat?: string; category?: string }): { items: Book[] } {
    return {
      items: memoryBooks.filter(
        (book) =>
          matchesQuery(book, filters?.query) &&
          (!filters?.bookFormat || book.bookFormat === filters.bookFormat) &&
          (!filters?.category || book.category === filters.category),
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
      title: "新しく見つかった書籍",
      author: "デモ著者",
      publisher: "デモ出版社",
      publishedDate: "2026-03-01",
      coverImageUrl: createMockCover("新しく見つかった書籍", "#9ab7da", "その他"),
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
      ...payload,
    };

    memoryBooks = [created, ...memoryBooks];
    return created;
  },
  deleteBook(isbn: string): void {
    memoryBooks = memoryBooks.filter((item) => item.isbn !== isbn);
  },
  reset(): void {
    memoryBooks = [...demoBooks];
  },
};
