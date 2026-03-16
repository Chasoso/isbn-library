export interface Book {
  userId: string;
  isbn: string;
  title: string;
  author: string;
  publisher: string;
  publishedDate: string;
  coverImageUrl: string;
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

export interface AuthState {
  isAuthenticated: boolean;
  accessToken: string | null;
  email: string | null;
  loading: boolean;
}
