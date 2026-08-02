import { History } from "lucide-react";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import { formatRelativeTime } from "@/lib/format";
import type { TimelineEvent } from "@/lib/mock/patients";

export function TimelineSection({ events }: { events: TimelineEvent[] }) {
  return (
    <SectionCard title="Timeline" description="Recent activity for this patient.">
      {events.length === 0 ? (
        <EmptyState icon={History} title="No recent activity" />
      ) : (
        <ol className="space-y-3">
          {events.map((event) => (
            <li key={event.event_id} className="flex items-start gap-3">
              <span
                className="mt-1.5 size-1.5 shrink-0 rounded-full bg-primary"
                aria-hidden="true"
              />
              <div className="space-y-0.5">
                <p className="text-sm">{event.description}</p>
                <p className="text-xs text-muted-foreground">
                  {formatRelativeTime(event.occurred_at)}
                </p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </SectionCard>
  );
}
