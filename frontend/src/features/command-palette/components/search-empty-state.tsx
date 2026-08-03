import { SearchX } from "lucide-react";

export function SearchEmptyState({ query }: { query: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-10 text-center">
      <SearchX className="size-8 text-muted-foreground" aria-hidden="true" />
      <p className="text-sm font-medium">No results for &ldquo;{query}&rdquo;</p>
      <p className="text-xs text-muted-foreground">Try a different name, ID, or keyword.</p>
    </div>
  );
}
