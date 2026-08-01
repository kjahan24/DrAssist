import { redirect } from "next/navigation";

// The app has no marketing/landing surface — `middleware.ts` already
// redirects unauthenticated requests to `/login` before this ever
// renders, so reaching here means a valid session cookie exists.
export default function RootPage() {
  redirect("/dashboard");
}
