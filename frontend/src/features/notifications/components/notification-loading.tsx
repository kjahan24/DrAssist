import { Skeleton } from "@/components/ui/skeleton";

// The loading state for the notification list — shown while
// `useNotifications()` is fetching. Mirrors the shape of a real date
// group (a date heading followed by a few notification rows) so the
// layout doesn't jump once real data arrives.
export function NotificationLoading() {
  return (
    <div className="space-y-6" aria-hidden="true">
      {Array.from({ length: 2 }).map((_, groupIndex) => (
        <div key={groupIndex} className="space-y-3">
          <Skeleton className="h-5 w-40" />
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, cardIndex) => (
              <div key={cardIndex} className="flex items-start gap-3 rounded-lg border p-4">
                <Skeleton className="size-9 shrink-0 rounded-full" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-1/3" />
                  <Skeleton className="h-3 w-2/3" />
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
