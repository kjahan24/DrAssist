import { CalendarCheck, FileText, FileUp, History, UserPlus, type LucideIcon } from "lucide-react";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { formatRelativeTime } from "@/lib/format";
import type { ActivityItem, ActivityType } from "@/lib/mock/doctor-dashboard";

const ACTIVITY_ICON: Record<ActivityType, LucideIcon> = {
  appointment_completed: CalendarCheck,
  soap_note_saved: FileText,
  document_uploaded: FileUp,
  patient_registered: UserPlus,
};

interface ActivityTimelineProps {
  items: ActivityItem[];
  isLoading?: boolean;
}

export function ActivityTimeline({ items, isLoading }: ActivityTimelineProps) {
  return (
    <SectionCard title="Recent Clinical Activity" description="What's happened recently.">
      {isLoading ? (
        <div className="space-y-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-10 w-full" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={History}
          title="No recent activity"
          description="Activity will appear here as it happens."
        />
      ) : (
        <ol className="space-y-4">
          {items.map((item, index) => {
            const Icon = ACTIVITY_ICON[item.type];
            return (
              <li key={item.activity_id} className="relative flex gap-3 pl-1">
                {index < items.length - 1 && (
                  <span
                    className="absolute left-[15px] top-7 h-full w-px bg-border"
                    aria-hidden="true"
                  />
                )}
                <div className="z-10 flex size-8 shrink-0 items-center justify-center rounded-full border bg-background">
                  <Icon className="size-4 text-muted-foreground" aria-hidden="true" />
                </div>
                <div className="flex-1 space-y-0.5 pb-1">
                  <p className="text-sm">{item.description}</p>
                  <p className="text-xs text-muted-foreground">
                    {formatRelativeTime(item.timestamp)}
                  </p>
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </SectionCard>
  );
}
