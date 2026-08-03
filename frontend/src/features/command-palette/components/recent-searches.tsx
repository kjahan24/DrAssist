import { Clock, History, Trash2 } from "lucide-react";

import { CommandGroup, CommandItem, CommandSeparator } from "@/components/ui/command";
import type { RecentEntry } from "@/features/command-palette/lib/recent-activity";

interface RecentSearchesProps {
  entries: RecentEntry[];
  onSelect: (entry: RecentEntry) => void;
  onClear: () => void;
}

// Shown alongside `QuickActions` while the search query is empty — a
// unified "Recent" list covering both recent search queries (re-running
// the search when picked) and recent command/result selections
// (navigating directly when picked), satisfying this task's "Recent
// searches" and "Recent commands" as one list rather than two, matching
// the singular `RecentSearches` name in this module's own reusable
// component list. A trailing "Clear Recent" item removes the whole list
// rather than a header-embedded button, so `heading` stays a plain
// string (cmdk's own convention).
export function RecentSearches({ entries, onSelect, onClear }: RecentSearchesProps) {
  if (entries.length === 0) return null;

  return (
    <>
      <CommandGroup heading="Recent">
        {entries.map((entry) => (
          <CommandItem key={entry.id} value={`recent-${entry.id}`} onSelect={() => onSelect(entry)}>
            {entry.kind === "search" ? (
              <History className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
            ) : (
              <Clock className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
            )}
            <div className="min-w-0 flex-1">
              <p className="truncate">{entry.label}</p>
              {entry.description && (
                <p className="truncate text-xs text-muted-foreground">{entry.description}</p>
              )}
            </div>
          </CommandItem>
        ))}
        <CommandItem value="recent-clear-all" onSelect={onClear} className="text-muted-foreground">
          <Trash2 className="size-4 shrink-0" aria-hidden="true" />
          Clear Recent
        </CommandItem>
      </CommandGroup>
      <CommandSeparator />
    </>
  );
}
