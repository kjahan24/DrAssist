import { Skeleton } from "@/components/ui/skeleton";

// The loading state for the timeline event list — shown while
// `usePatientTimeline()` is fetching. Mirrors the shape of a real
// `TimelineDateGroup` (a date heading followed by a few event rows) so
// the layout doesn't jump once real data arrives.
export function TimelineLoading() {
  return (
    <div className="space-y-6" aria-hidden="true">
      {Array.from({ length: 3 }).map((_, groupIndex) => (
        <div key={groupIndex} className="space-y-3">
          <Skeleton className="h-5 w-48" />
          <div className="space-y-3">
            {Array.from({ length: 2 }).map((_, cardIndex) => (
              <div key={cardIndex} className="flex gap-4">
                <Skeleton className="size-8 shrink-0 rounded-full" />
                <div className="flex-1 space-y-2 rounded-lg border p-4">
                  <Skeleton className="h-4 w-1/3" />
                  <Skeleton className="h-3 w-1/4" />
                  <Skeleton className="h-4 w-full" />
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
