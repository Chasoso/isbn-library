import { config } from "../config";
import type { Book, BookLookupResult } from "../types";

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

export const getBooks = async (
  accessToken: string,
  query?: string,
): Promise<{ items: Book[] }> => {
  const search = query ? `?q=${encodeURIComponent(query)}` : "";
  return request<{ items: Book[] }>(`/books${search}`, accessToken);
};

export const getBook = async (
  accessToken: string,
  isbn: string,
): Promise<Book> => request<Book>(`/books/${isbn}`, accessToken);

export const createBook = async (
  accessToken: string,
  payload: BookLookupResult,
): Promise<Book> =>
  request<Book>("/books", accessToken, {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const deleteBook = async (
  accessToken: string,
  isbn: string,
): Promise<void> =>
  request<void>(`/books/${isbn}`, accessToken, {
    method: "DELETE",
  });

export const lookupBook = async (
  accessToken: string,
  isbn: string,
): Promise<BookLookupResult> => request<BookLookupResult>(`/lookup/${isbn}`, accessToken);
