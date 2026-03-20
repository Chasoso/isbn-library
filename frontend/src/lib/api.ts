import { config } from "../config";
import type { Book, BookLookupResult, CreateBookPayload } from "../types";
import { mockSession } from "./mockData";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

const request = async <T>(
  path: string,
  accessToken: string,
  init?: RequestInit,
): Promise<T> => {
  const response = await fetch(`${config.apiBaseUrl}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
      ...(init?.headers ?? {}),
    },
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const payload = (await response.json().catch(() => ({}))) as { message?: string };

  if (!response.ok) {
    throw new ApiError(payload.message ?? "API request failed", response.status);
  }

  return payload as T;
};

const ensureMockBook = (isbn: string): Book => {
  try {
    return mockSession.getBook(isbn);
  } catch {
    throw new ApiError("Book not found", 404);
  }
};

export const getBooks = async (
  accessToken: string,
  filters?: {
    query?: string;
    bookFormat?: string;
    category?: string;
    readingStatus?: string;
  },
): Promise<{ items: Book[] }> => {
  if (config.e2eDemoMode) {
    return mockSession.getBooks(filters);
  }

  const params = new URLSearchParams();

  if (filters?.query) {
    params.set("q", filters.query);
  }

  if (filters?.bookFormat) {
    params.set("bookFormat", filters.bookFormat);
  }

  if (filters?.category) {
    params.set("category", filters.category);
  }

  if (filters?.readingStatus) {
    params.set("readingStatus", filters.readingStatus);
  }

  const search = params.toString();
  return request<{ items: Book[] }>(`/books${search ? `?${search}` : ""}`, accessToken);
};

export const getBook = async (accessToken: string, isbn: string): Promise<Book> => {
  if (config.e2eDemoMode) {
    return ensureMockBook(isbn);
  }

  return request<Book>(`/books/${isbn}`, accessToken);
};

export const createBook = async (
  accessToken: string,
  payload: CreateBookPayload,
): Promise<Book> => {
  if (config.e2eDemoMode) {
    try {
      return mockSession.createBook(payload);
    } catch {
      throw new ApiError("Book already exists", 409);
    }
  }

  return request<Book>("/books", accessToken, {
    method: "POST",
    body: JSON.stringify(payload),
  });
};

export const deleteBook = async (accessToken: string, isbn: string): Promise<void> => {
  if (config.e2eDemoMode) {
    mockSession.deleteBook(isbn);
    return;
  }

  return request<void>(`/books/${isbn}`, accessToken, {
    method: "DELETE",
  });
};

export const lookupBook = async (
  accessToken: string,
  isbn: string,
): Promise<BookLookupResult> => {
  if (config.e2eDemoMode) {
    return mockSession.lookupBook(isbn);
  }

  return request<BookLookupResult>(`/lookup/${isbn}`, accessToken);
};

export const updateBookStatus = async (
  accessToken: string,
  isbn: string,
  readingStatus: string,
): Promise<Book> => {
  if (config.e2eDemoMode) {
    return mockSession.updateBookStatus(isbn, readingStatus);
  }

  return request<Book>(`/books/${isbn}/status`, accessToken, {
    method: "PATCH",
    body: JSON.stringify({ readingStatus }),
  });
};
