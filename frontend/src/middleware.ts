import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { AUTH_TOKEN_COOKIE } from "@/lib/constants";

// Route-level auth gate, running at the edge before any page renders. This
// is a presence check only — it never validates the token itself (the
// backend's `get_current_user` dependency is the sole authority on
// validity) — so it can only ever produce a misleading redirect, never a
// false grant of access. See `lib/auth/token-storage.ts` for why a cookie
// (not localStorage) is what makes this possible at all.
//
// Allowlist-shaped on purpose: only `/dashboard/*` is actually protected,
// and `/login` is public-but-redirects-away-if-authenticated. Everything
// else (the marketing site, and any unrecognized path) falls straight
// through to Next.js's own router — otherwise a typo'd marketing URL like
// `/pricng` would bounce a visitor to a login form instead of a normal
// 404, which is exactly the bug an earlier, denylist-shaped version of
// this file had.
const AUTH_ONLY_ROUTE = "/login";
const PROTECTED_PREFIX = "/dashboard";

function isProtectedRoute(pathname: string): boolean {
  return pathname === PROTECTED_PREFIX || pathname.startsWith(`${PROTECTED_PREFIX}/`);
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasToken = request.cookies.has(AUTH_TOKEN_COOKIE);

  if (pathname === AUTH_ONLY_ROUTE) {
    return hasToken
      ? NextResponse.redirect(new URL("/dashboard", request.url))
      : NextResponse.next();
  }

  if (isProtectedRoute(pathname) && !hasToken) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("from", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)"],
};
