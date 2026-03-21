import type { BookFormat } from "./catalog";
import type { ReadingStatus } from "./readingStatus";

export interface CategoryDefinition {
  categoryId: string;
  name: string;
  sortOrder: number;
  color?: string;
  createdAt: string;
  updatedAt: string;
}

export interface Book {
  userId: string;
  isbn: string;
  title: string;
  author: string;
  publisher: string;
  publishedDate: string;
  coverImageUrl: string;
  bookFormat: BookFormat;
  categoryId: string;
  categoryName: string;
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
  categoryId: string;
  readingStatus: ReadingStatus;
}

export interface CreateCategoryPayload {
  name: string;
  color?: string;
}

export interface UpdateCategoryPayload {
  name?: string;
  color?: string;
  sortOrder?: number;
}

export interface AuthState {
  isAuthenticated: boolean;
  accessToken: string | null;
  email: string | null;
  name: string | null;
  loading: boolean;
}
