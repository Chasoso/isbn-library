import type { Book, BookLookupResult, CreateBookPayload } from "../types";

const demoBooks: Book[] = [
  {
    userId: "demo-user",
    isbn: "9784860648114",
    title: "ネイティブが日常会話でよく使っている表現フレーズ大全",
    author: "Blake Turnbull",
    publisher: "ベレ出版",
    publishedDate: "2024-03-12",
    coverImageUrl: "https://books.google.com/books/content?id=4f4rEQAAQBAJ&printsec=frontcover&img=1&zoom=1&source=gbs_api",
    bookFormat: "単行本",
    category: "ビジネス",
    createdAt: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
  },
  {
    userId: "demo-user",
    isbn: "9784798183251",
    title: "優れたエンジニアがコミュニティの中でしていること",
    author: "吉住 佳, 藤井 玲, 宮本 佳世",
    publisher: "翔泳社",
    publishedDate: "2025-01-20",
    coverImageUrl: "https://books.google.com/books/content?id=8CU8EQAAQBAJ&printsec=frontcover&img=1&zoom=1&source=gbs_api",
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
    coverImageUrl: "https://books.google.com/books/content?id=2oX9zgEACAAJ&printsec=frontcover&img=1&zoom=1&source=gbs_api",
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
    coverImageUrl: "https://books.google.com/books/content?id=zfsm0AEACAAJ&printsec=frontcover&img=1&zoom=1&source=gbs_api",
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
    coverImageUrl: "https://books.google.com/books/content?id=7upn0AEACAAJ&printsec=frontcover&img=1&zoom=1&source=gbs_api",
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
    coverImageUrl: "",
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
      coverImageUrl: "",
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
