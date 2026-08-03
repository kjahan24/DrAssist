import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

// Required by shadcn/ui components — merges conditional class names and
// resolves Tailwind class conflicts (e.g. "p-2 p-4" -> "p-4").
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Shared `Avatar`/`AvatarFallback` initials helper — consolidated here
// from a dozen byte-identical copies scattered across feature modules'
// own identity/card/column components. Takes a single display name (not
// a structured first/last-name pair), so it's distinct from
// `lib/mock/patients.ts`'s own `getInitials(patient)` (which derives
// initials from `first_name`/`last_name` directly) and
// `components/layout/user-nav.tsx`'s `getInitials(email)` (no name
// available before a user has one) — those two stay as-is.
export function getInitials(name: string): string {
  return name
    .split(" ")
    .map((part) => part[0] ?? "")
    .join("")
    .slice(0, 2)
    .toUpperCase();
}
