import { History } from "lucide-react";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import { AppointmentStatusBadge } from "@/features/appointments/components/appointment-status-badge";
import { formatDateTime } from "@/lib/format";
import type { AppointmentStatusHistoryEntry } from "@/lib/mock/appointments";

// Renders the appointment's status transition log. The real backend has
// no queryable transition history (only a single `AppointmentStatusChanged`
// domain event per change) — see `lib/mock/appointments.ts`'s docstring —
// so this section is presentational-only until that's added.
export function AppointmentTimeline({ history }: { history: AppointmentStatusHistoryEntry[] }) {
  return (
    <SectionCard title="Status History" description="How this appointment's status has changed.">
      {history.length === 0 ? (
        <EmptyState icon={History} title="No status changes yet" />
      ) : (
        <ol className="space-y-3">
          {history.map((entry, index) => (
            <li key={`${entry.status}-${entry.changed_at}`} className="flex items-start gap-3">
              <span
                className="mt-1.5 size-1.5 shrink-0 rounded-full bg-primary"
                aria-hidden="true"
              />
              <div className="min-w-0 flex-1 space-y-0.5">
                <div className="flex flex-wrap items-center gap-2">
                  <AppointmentStatusBadge status={entry.status} />
                  {index === history.length - 1 && (
                    <span className="text-xs font-medium text-muted-foreground">Current</span>
                  )}
                </div>
                <p className="text-xs text-muted-foreground">{formatDateTime(entry.changed_at)}</p>
                {entry.note && <p className="text-sm">{entry.note}</p>}
              </div>
            </li>
          ))}
        </ol>
      )}
    </SectionCard>
  );
}
