"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Command, CommandList } from "@/components/ui/command";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { QuickActions } from "@/features/command-palette/components/quick-actions";
import { RecentSearches } from "@/features/command-palette/components/recent-searches";
import { SearchEmptyState } from "@/features/command-palette/components/search-empty-state";
import { SearchInput } from "@/features/command-palette/components/search-input";
import { SearchLoading } from "@/features/command-palette/components/search-loading";
import { SearchResultList } from "@/features/command-palette/components/search-result-list";
import { useGlobalSearch } from "@/features/command-palette/hooks/use-global-search";
import type { SearchResult } from "@/features/command-palette/lib/global-search";
import type { QuickAction } from "@/features/command-palette/lib/quick-actions";
import { getSearchEntityLabel } from "@/features/command-palette/lib/result-visuals";
import {
  addRecentEntry,
  clearRecentEntries,
  getRecentEntries,
  type RecentEntry,
} from "@/features/command-palette/lib/recent-activity";
import { useDebounce } from "@/hooks/use-debounce";

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// The Command Palette itself (Ctrl+K / Cmd+K). Composed from `Dialog` +
// `Command` directly (not shadcn's own `CommandDialog`) specifically so
// `shouldFilter={false}` can be set on `Command` — this palette does its
// own server-shaped search via `searchAll()`/`useGlobalSearch()` rather
// than `cmdk`'s built-in client-side fuzzy filter, the same
// `shouldFilter={false}` + externally-controlled query pattern already
// established in `features/appointments/components/patient-combobox.tsx`.
// `cmdk`'s `Command`/`CommandList`/`CommandItem` still supply keyboard
// navigation (arrow keys, Enter) for free; `Dialog` supplies Escape and
// focus trapping. `open` is owned by the caller (`CommandPaletteTrigger`)
// since the global Ctrl+K listener needs to toggle the same state a
// visible trigger button also opens.
export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [recents, setRecents] = useState<RecentEntry[]>([]);
  const debouncedQuery = useDebounce(query, 200);
  const { data: results, isLoading, isFetching } = useGlobalSearch(debouncedQuery);

  useEffect(() => {
    if (open) setRecents(getRecentEntries());
  }, [open]);

  function close() {
    onOpenChange(false);
    setQuery("");
  }

  function navigate(href: string) {
    close();
    router.push(href);
  }

  function handleSelectResult(result: SearchResult) {
    setRecents(
      addRecentEntry({
        kind: "navigation",
        label: result.title,
        description: getSearchEntityLabel(result.entity_type),
        href: result.href,
      }),
    );
    if (debouncedQuery.length > 0) {
      addRecentEntry({ kind: "search", label: debouncedQuery, query: debouncedQuery });
    }
    navigate(result.href);
  }

  function handleSelectQuickAction(action: QuickAction) {
    setRecents(addRecentEntry({ kind: "navigation", label: action.label, href: action.href }));
    navigate(action.href);
  }

  function handleSelectRecent(entry: RecentEntry) {
    if (entry.kind === "search") {
      setQuery(entry.query ?? entry.label);
      return;
    }
    if (entry.href) navigate(entry.href);
  }

  function handleClearRecents() {
    setRecents(clearRecentEntries());
  }

  const hasQuery = debouncedQuery.length > 0;
  const showLoading = hasQuery && (isLoading || isFetching);
  const showResults = hasQuery && !showLoading && (results?.length ?? 0) > 0;
  const showNoResults = hasQuery && !showLoading && (results?.length ?? 0) === 0;

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        onOpenChange(next);
        if (!next) setQuery("");
      }}
    >
      <DialogContent className="overflow-hidden p-0 sm:max-w-xl">
        <DialogTitle className="sr-only">Search</DialogTitle>
        <DialogDescription className="sr-only">
          Search across patients, appointments, and every other record, or run a quick action.
        </DialogDescription>
        <Command
          shouldFilter={false}
          className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-muted-foreground [&_[cmdk-group]:not([hidden])_~[cmdk-group]]:pt-0 [&_[cmdk-group]]:px-2 [&_[cmdk-input-wrapper]_svg]:size-5 [&_[cmdk-input]]:h-12 [&_[cmdk-item]]:px-2 [&_[cmdk-item]]:py-3"
        >
          <SearchInput value={query} onChange={setQuery} />
          <CommandList>
            {!hasQuery && (
              <>
                <RecentSearches
                  entries={recents}
                  onSelect={handleSelectRecent}
                  onClear={handleClearRecents}
                />
                <QuickActions onSelect={handleSelectQuickAction} />
              </>
            )}
            {showLoading && <SearchLoading />}
            {showResults && (
              <SearchResultList
                results={results ?? []}
                query={debouncedQuery}
                onSelect={handleSelectResult}
              />
            )}
            {showNoResults && <SearchEmptyState query={debouncedQuery} />}
          </CommandList>
        </Command>
      </DialogContent>
    </Dialog>
  );
}
