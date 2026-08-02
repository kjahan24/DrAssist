import Cookies from "js-cookie";

import { AUTH_TOKEN_COOKIE } from "@/lib/constants";

// A regular (non-httpOnly) cookie, not localStorage: `middleware.ts` runs
// on the edge runtime and can only read cookies, not browser storage, so
// this is what makes route-level auth guarding possible without a network
// round-trip. This only gates navigation — every real request is still
// authorized server-side by the backend's own token validation
// (`get_current_user`), so a missing/forged cookie value can only ever
// cause a misleading client-side redirect, never real unauthorized access.
const BASE_COOKIE_OPTIONS: Cookies.CookieAttributes = {
  sameSite: "lax",
  secure: process.env.NODE_ENV === "production",
};

// "Remember Me" (Login form) is a genuine, backend-independent behavior
// difference, not a cosmetic checkbox: unchecked, the cookie is
// session-only (cleared when the browser closes, via Cookies.js's
// `expires: undefined`); checked, it survives for 30 days. Neither case
// changes what the token itself is or how long the *backend* considers it
// valid — that's still entirely up to the JWT's own expiry.
export const tokenStorage = {
  get(): string | undefined {
    return Cookies.get(AUTH_TOKEN_COOKIE);
  },
  set(token: string, options: { rememberMe?: boolean } = {}): void {
    Cookies.set(AUTH_TOKEN_COOKIE, token, {
      ...BASE_COOKIE_OPTIONS,
      expires: options.rememberMe ? 30 : undefined,
    });
  },
  clear(): void {
    Cookies.remove(AUTH_TOKEN_COOKIE);
  },
};
