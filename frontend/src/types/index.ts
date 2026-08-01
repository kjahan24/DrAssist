// Shared, cross-feature TypeScript types. Feature-local types should live
// alongside their feature under src/features/<feature>/types.ts instead.

// Mirrors `app.schemas.base.PaginatedResponse` exactly (`items`, `total`,
// `offset`, `limit` plus its two `@computed_field`s) — every list endpoint
// across all backend modules returns this same envelope.
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
  page: number;
  page_size: number;
}

// Mirrors `app.middlewares.error_handler`'s JSON error body exactly.
export interface ApiErrorResponse {
  error_code: string;
  message: string;
  details?: unknown;
}

// Mirrors `app.modules.authentication.application.dto
// .AuthenticatedPrincipalDTO` — deliberately narrow (identity + effective
// permissions), never the full `User` aggregate. Field names are kept in
// the backend's own snake_case (not camelCased) so a type stays a
// trustworthy 1:1 map of the wire shape.
export interface AuthenticatedPrincipal {
  user_id: string;
  organization_id: string;
  session_id: string;
  email: string;
  permissions: string[];
}
