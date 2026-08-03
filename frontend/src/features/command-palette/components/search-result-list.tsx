import { CommandGroup } from "@/components/ui/command";
import { SearchResultItem } from "@/features/command-palette/components/search-result-item";
import { getSearchEntityLabel } from "@/features/command-palette/lib/result-visuals";
import type { SearchEntityType, SearchResult } from "@/features/command-palette/lib/global-search";

interface SearchResultListProps {
  results: SearchResult[];
  query: string;
  onSelect: (result: SearchResult) => void;
}

// Groups a flat `SearchResult[]` by entity type into one `CommandGroup`
// per category (Patients, Appointments, ...) — assumes `results` is
// already non-empty; the caller (`CommandPalette`) decides between this,
// `SearchLoading`, and `SearchEmptyState`.
export function SearchResultList({ results, query, onSelect }: SearchResultListProps) {
  const groups = new Map<SearchEntityType, SearchResult[]>();
  for (const result of results) {
    const bucket = groups.get(result.entity_type);
    if (bucket) {
      bucket.push(result);
    } else {
      groups.set(result.entity_type, [result]);
    }
  }

  return (
    <>
      {Array.from(groups.entries()).map(([entityType, groupResults]) => (
        <CommandGroup key={entityType} heading={getSearchEntityLabel(entityType)}>
          {groupResults.map((result) => (
            <SearchResultItem key={result.id} result={result} query={query} onSelect={onSelect} />
          ))}
        </CommandGroup>
      ))}
    </>
  );
}
