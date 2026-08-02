import { CalendarDays } from "lucide-react";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate } from "@/lib/format";
import type { UpcomingCalendarItem } from "@/lib/mock/doctor-dashboard";

interface CalendarPreviewProps {
  items: UpcomingCalendarItem[];
  isLoading?: boolean;
}

// A glance-ahead preview only — deliberately not a full calendar (out of
// scope for this module).
export function CalendarPreview({ items, isLoading }: CalendarPreviewProps) {
  return (
    <SectionCard title="Upcoming" description="What's coming up next.">
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <Skeleton key={index} className="h-12 w-full" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={CalendarDays}
          title="Nothing scheduled"
          description="No upcoming appointments yet."
        />
      ) : (
        <ul className="space-y-3">
          {items.map((item, index) => (
            <li key={index} className="flex items-center gap-3 text-sm">
              <div className="flex size-11 shrink-0 flex-col items-center justify-center rounded-lg border">
                <span className="text-[10px] font-medium uppercase text-muted-foreground">
                  {formatDate(item.date, "MMM")}
                </span>
                <span className="text-sm font-semibold leading-none">
                  {formatDate(item.date, "d")}
                </span>
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium">{item.patient_name}</p>
                <p className="text-xs text-muted-foreground">
                  {item.visit_type} · {item.time}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </SectionCard>
  );
}
