import axios, { type AxiosError } from "axios";

import { ApiError } from "@/lib/api-error";
import { tokenStorage } from "@/lib/auth/token-storage";
import { env } from "@/config/env";
import type { ApiErrorResponse } from "@/types";

// Re-exported so existing consumers that need both the error type and
// the live client (`import { ApiError, httpClient } from
// "@/lib/api-client"` — the real backend-integrated auth pages) don't
// need two import lines. See `lib/api-error.ts` for why the class itself
// lives there instead of here.
export { ApiError };

// Single Axios instance every feature module's API client is built on top
// of. Feature modules should never construct their own instance — that
// would bypass the auth header injection and 401 handling below.
export const httpClient = axios.create({
  baseURL: env.NEXT_PUBLIC_API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

httpClient.interceptors.request.use((config) => {
  const token = tokenStorage.get();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

httpClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiErrorResponse>) => {
    if (error.response) {
      const { status, data } = error.response;

      // A 401 means the token is missing/expired/revoked — the backend's
      // `get_current_user` dependency is the sole source of truth here,
      // never a client-side expiry check. Clearing state and bouncing out
      // is a hard redirect (not a router push) so it also works from
      // outside React's render tree, e.g. a TanStack Query retry.
      //
      // Distinguishing the two 401 cases matters for UX: a request that
      // had a token which the backend then rejected means a real session
      // just ended (`/session-expired`, which explains what happened and
      // offers a way back in); a request with no token at all was never
      // authenticated in the first place, so a plain `/login` is correct
      // with no extra explanation needed.
      if (status === 401) {
        const hadToken = Boolean(tokenStorage.get());
        tokenStorage.clear();
        if (typeof window !== "undefined") {
          window.location.href = hadToken ? "/session-expired" : "/login";
        }
      }

      return Promise.reject(
        new ApiError(
          data?.message ?? error.message,
          status,
          data?.error_code ?? "unknown_error",
          data?.details,
        ),
      );
    }

    // Request never got a response at all (network down, CORS, timeout).
    return Promise.reject(new ApiError(error.message, 0, "network_error"));
  },
);
