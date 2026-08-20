import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { AUTH_TOKEN_COOKIE } from "@/lib/constants";

// Route-level auth gate, running at the edge before any page renders. This
// is a *plausibility* check, not real validation — the backend's
// `get_current_user` dependency remains the sole authority on whether a
// token is actually valid (still signature-verified, still checked
// against the live user/session, only ever server-side); the edge never
// sees the signing secret and never should. See
// `lib/auth/token-storage.ts` for why a cookie (not localStorage) is what
// makes this possible at all.
//
// `hasPlausibleSession` used to be a bare cookie-presence check
// (`request.cookies.has(...)`), which meant *any* leftover cookie value —
// garbage from a previous bad response, or a genuinely expired token that
// outlived its own session without ever triggering the client-side 401
// handler that normally clears it (e.g. the tab was closed, not
// navigated) — was enough to redirect a real visitor away from
// `/register`/`/login` and into `/dashboard`, which does not itself
// re-validate the token against the backend before rendering. That
// combination silently locked such a visitor out of ever reaching the
// sign-up/sign-in forms again. Decoding (never verifying) the token's own
// `exp` claim catches both cases — a non-JWT string and a JWT past its
// own expiry both now correctly read as "no session" — without granting
// anything: a well-formed, unexpired-looking token that the backend then
// rejects still can't grant access to `/dashboard`, it just avoids the
// bounce away from the auth pages a genuinely invalid one no longer causes.
//
// Allowlist-shaped on purpose: only `/dashboard/*` is actually protected,
// and a small set of "you're not signed in yet" auth pages redirect away
// if a session already exists. Everything else (the marketing site,
// email-verification/status pages, and any unrecognized path) falls
// straight through to Next.js's own router — otherwise a typo'd marketing
// URL like `/pricng` would bounce a visitor to a login form instead of a
// normal 404, which is exactly the bug an earlier, denylist-shaped
// version of this file had.
//
// Only pages whose entire purpose is "establish a session you don't have
// yet" redirect away when one already exists — Register/Forgot/Reset
// Password join Login here for the same reason. Verify-email and the
// status pages (session-expired/unauthorized/access-denied) do NOT: a
// signed-in user can legitimately land on any of those (e.g. clicking a
// verification link from a second device, or a stale bookmark), and
// forcing them off would be more confusing than just letting the page
// render.
const AUTH_ONLY_ROUTES = ["/login", "/register", "/forgot-password", "/reset-password"];
const PROTECTED_PREFIX = "/dashboard";

function isProtectedRoute(pathname: string): boolean {
  return pathname === PROTECTED_PREFIX || pathname.startsWith(`${PROTECTED_PREFIX}/`);
}

// Decodes (never verifies — no secret is available or should be at the
// edge) a JWT's payload segment just far enough to read `exp`. Returns
// `false` for anything that isn't even shaped like a JWT (three
// dot-separated base64url segments with a JSON payload) or whose `exp`
// has already passed. Deliberately fails closed: any decode error means
// "not a plausible session," never the reverse.
function hasUnexpiredJwtShape(token: string): boolean {
  const parts = token.split(".");
  const payloadSegment = parts[1];
  if (parts.length !== 3 || payloadSegment === undefined) return false;
  try {
    const base64 = payloadSegment.replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
    const payload = JSON.parse(atob(padded)) as { exp?: unknown };
    return typeof payload.exp === "number" && payload.exp * 1000 > Date.now();
  } catch {
    return false;
  }
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const rawToken = request.cookies.get(AUTH_TOKEN_COOKIE)?.value;
  const hasPlausibleSession = rawToken !== undefined && hasUnexpiredJwtShape(rawToken);

  if (AUTH_ONLY_ROUTES.includes(pathname)) {
    return hasPlausibleSession
      ? NextResponse.redirect(new URL("/dashboard", request.url))
      : NextResponse.next();
  }

  if (isProtectedRoute(pathname) && !hasPlausibleSession) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("from", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)"],
};
