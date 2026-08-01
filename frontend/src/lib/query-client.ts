import { QueryClient } from "@tanstack/react-query";

import { ApiError } from "@/lib/api-client";

// A fresh QueryClient per call — required for SSR/RSC (a module-level
// singleton would leak cached data across requests/users); `providers.tsx`
// memoizes one instance for the lifetime of the browser session via
// `useState`, the pattern TanStack Query's own Next.js App Router guide
// recommends.
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: false,
        retry: (failureCount, error) => {
          // 4xx means the request itself was wrong (bad input, not found,
          // forbidden) — retrying an identical request can't fix that.
          if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
            return false;
          }
          return failureCount < 2;
        },
      },
      mutations: {
        retry: false,
      },
    },
  });
}
