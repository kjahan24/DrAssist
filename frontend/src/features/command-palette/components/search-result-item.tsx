import { CommandItem } from "@/components/ui/command";
import { HighlightMatch } from "@/features/command-palette/lib/highlight-match";
import {
  getSearchEntityLabel,
  getSearchResultIcon,
} from "@/features/command-palette/lib/result-visuals";
import type { SearchResult } from "@/features/command-palette/lib/global-search";

interface SearchResultItemProps {
  result: SearchResult;
  query: string;
  onSelect: (result: SearchResult) => void;
}

// One row in `SearchResultList` — icon, entity type, title, subtitle,
// with the matched query substring highlighted in both title and
// subtitle. `cmdk`'s own `CommandItem` supplies the keyboard
// navigation/selection behavior (arrow keys, Enter) for free.
export function SearchResultItem({ result, query, onSelect }: SearchResultItemProps) {
  const Icon = getSearchResultIcon(result.entity_type);

  return (
    <CommandItem
      value={result.id}
      onSelect={() => onSelect(result)}
      className="flex items-center gap-3"
    >
      <Icon className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">
          <HighlightMatch text={result.title} query={query} />
        </p>
        <p className="truncate text-xs text-muted-foreground">
          <HighlightMatch text={result.subtitle} query={query} />
        </p>
      </div>
      <span className="shrink-0 text-xs text-muted-foreground">
        {getSearchEntityLabel(result.entity_type)}
      </span>
    </CommandItem>
  );
}
