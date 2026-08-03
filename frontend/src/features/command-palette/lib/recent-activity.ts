// Recent searches/commands for the Command Palette, persisted to
// `localStorage`. This is client-only UI state (exactly the same
// category as `next-themes`'s own persisted theme choice, see
// `components/layout/theme-toggle.tsx`), not mock business data — it
// never represents anything a real backend would own, so it
// deliberately does not live in `lib/mock/`.

const STORAGE_KEY = "drassist:command-palette:recent";
const MAX_ENTRIES = 8;

export interface RecentEntry {
  id: string;
  kind: "search" | "navigation";
  label: string;
  description?: string;
  href?: string;
  query?: string;
  timestamp: number;
}

function readStorage(): RecentEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as RecentEntry[]) : [];
  } catch {
    return [];
  }
}

function writeStorage(entries: RecentEntry[]): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
  } catch {
    // Storage can legitimately fail (private browsing, quota) — recents
    // are a convenience, not a feature anything else depends on, so a
    // failed write is silently ignored rather than surfaced to the user.
  }
}

export function getRecentEntries(): RecentEntry[] {
  return readStorage();
}

// De-duplicates by `kind` + `label` (re-picking something already in the
// list just moves it back to the front, rather than showing it twice).
export function addRecentEntry(entry: Omit<RecentEntry, "id" | "timestamp">): RecentEntry[] {
  const existing = readStorage().filter(
    (item) => !(item.kind === entry.kind && item.label === entry.label),
  );
  const next: RecentEntry[] = [
    { ...entry, id: `${entry.kind}-${Date.now()}`, timestamp: Date.now() },
    ...existing,
  ].slice(0, MAX_ENTRIES);
  writeStorage(next);
  return next;
}

export function clearRecentEntries(): RecentEntry[] {
  writeStorage([]);
  return [];
}
