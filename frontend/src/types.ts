import type { BookFormat, Category } from "./catalog";
import type { ReadingStatus } from "./readingStatus";

export interface Book {
  userId: string;
  isbn: string;
  title: string;
  author: string;
  publisher: string;
  publishedDate: string;
  coverImageUrl: string;
  bookFormat: BookFormat;
  category: Category;
  readingStatus: ReadingStatus;
  createdAt: string;
}

export interface BookLookupResult {
  isbn: string;
  title: string;
  author: string;
  publisher: string;
  publishedDate: string;
  coverImageUrl: string;
}

export interface CreateBookPayload extends BookLookupResult {
  bookFormat: BookFormat;
  category: Category;
  readingStatus: ReadingStatus;
}

export interface AuthState {
  isAuthenticated: boolean;
  accessToken: string | null;
  email: string | null;
  name: string | null;
  loading: boolean;
}
