import axios, { type AxiosError } from "axios";

import { tokenStorage } from "@/lib/auth/token-storage";
import { env } from "@/config/env";
import type { ApiErrorResponse } from "@/types";

// Normalized shape every failed request rejects with, regardless of
// whether the backend returned a structured error body, a plain HTTP
// failure, or the request never reached the server at all. Mirrors
// `app.middlewares.error_handler`'s `{error_code, message, details?}`
// JSON shape exactly — see that file for the backend-side contract.
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly errorCode: string,
    public readonly details?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

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
      // never a client-side expiry check. Clearing state and bouncing to
      // `/login` is a hard redirect (not a router push) so it also works
      // from outside React's render tree, e.g. a TanStack Query retry.
      if (status === 401) {
        tokenStorage.clear();
        if (typeof window !== "undefined") {
          window.location.href = "/login";
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
