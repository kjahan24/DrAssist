import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

// Required by shadcn/ui components — merges conditional class names and
// resolves Tailwind class conflicts (e.g. "p-2 p-4" -> "p-4").
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
