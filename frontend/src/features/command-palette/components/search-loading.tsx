import { Skeleton } from "@/components/ui/skeleton";

// Shown while the debounced `searchAll()` call is in flight.
export function SearchLoading() {
  return (
    <div className="space-y-2 p-2" aria-hidden="true">
      {Array.from({ length: 4 }).map((_, index) => (
        <div key={index} className="flex items-center gap-3 px-2 py-1.5">
          <Skeleton className="size-4 shrink-0 rounded-full" />
          <div className="flex-1 space-y-1.5">
            <Skeleton className="h-3.5 w-1/3" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}
