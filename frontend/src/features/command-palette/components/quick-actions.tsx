import { ArrowRight } from "lucide-react";

import { CommandGroup, CommandItem } from "@/components/ui/command";
import { QUICK_ACTIONS, type QuickAction } from "@/features/command-palette/lib/quick-actions";

interface QuickActionsProps {
  onSelect: (action: QuickAction) => void;
}

// The palette's "Quick Actions" group — shown when the search query is
// empty, alongside `RecentSearches`. Every action navigates to a real,
// already-built page; none perform a mutation directly (see this task's
// own "Quick navigation (UI)" wording).
export function QuickActions({ onSelect }: QuickActionsProps) {
  return (
    <CommandGroup heading="Quick Actions">
      {QUICK_ACTIONS.map((action) => (
        <CommandItem
          key={action.id}
          value={`quick-action-${action.id}`}
          onSelect={() => onSelect(action)}
        >
          <ArrowRight className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
          {action.label}
        </CommandItem>
      ))}
    </CommandGroup>
  );
}
