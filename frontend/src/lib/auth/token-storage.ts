import Cookies from "js-cookie";

import { AUTH_TOKEN_COOKIE } from "@/lib/constants";

// A regular (non-httpOnly) cookie, not localStorage: `middleware.ts` runs
// on the edge runtime and can only read cookies, not browser storage, so
// this is what makes route-level auth guarding possible without a network
// round-trip. This only gates navigation — every real request is still
// authorized server-side by the backend's own token validation
// (`get_current_user`), so a missing/forged cookie value can only ever
// cause a misleading client-side redirect, never real unauthorized access.
const COOKIE_OPTIONS: Cookies.CookieAttributes = {
  expires: 1,
  sameSite: "lax",
  secure: process.env.NODE_ENV === "production",
};

export const tokenStorage = {
  get(): string | undefined {
    return Cookies.get(AUTH_TOKEN_COOKIE);
  },
  set(token: string): void {
    Cookies.set(AUTH_TOKEN_COOKIE, token, COOKIE_OPTIONS);
  },
  clear(): void {
    Cookies.remove(AUTH_TOKEN_COOKIE);
  },
};
