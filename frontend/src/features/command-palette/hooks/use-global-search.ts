"use client";

import { useQuery } from "@tanstack/react-query";

import { searchAll } from "@/features/command-palette/lib/global-search";
import { createQueryKeys } from "@/lib/query-keys";

// Same `createQueryKeys` factory every feature module uses, keyed by the
// debounced query string — swapping `searchAll()` for a real aggregated
// search endpoint later touches only `global-search.ts`, not this hook
// or any component.
export const searchKeys = createQueryKeys<{ query: string }>("global-search");

export function useGlobalSearch(query: string) {
  const trimmed = query.trim();

  return useQuery({
    queryKey: searchKeys.list({ query: trimmed }),
    queryFn: () => searchAll(trimmed),
    enabled: trimmed.length > 0,
  });
}
