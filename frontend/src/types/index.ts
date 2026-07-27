// Shared, cross-feature TypeScript types. Feature-local types should live
// alongside their feature under src/features/<feature>/types.ts instead.

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
}

export interface ApiErrorResponse {
  error_code: string;
  message: string;
  details?: unknown;
}
