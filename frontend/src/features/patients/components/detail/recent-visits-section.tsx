import { CalendarDays } from "lucide-react";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/format";
import type { RecentVisit } from "@/lib/mock/patients";

export function RecentVisitsSection({ visits }: { visits: RecentVisit[] }) {
  return (
    <SectionCard title="Recent Visits" description="This patient's most recent visits.">
      {visits.length === 0 ? (
        <EmptyState icon={CalendarDays} title="No visits on file" />
      ) : (
        <ul className="divide-y">
          {visits.map((visit) => (
            <li
              key={visit.visit_id}
              className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0"
            >
              <div className="min-w-0 space-y-0.5">
                <p className="truncate text-sm font-medium">{visit.reason_for_visit}</p>
                <p className="text-xs text-muted-foreground">
                  {visit.visit_type} · {formatDate(visit.visit_date)} · {visit.doctor_name}
                </p>
              </div>
              <Badge variant="outline" className="shrink-0">
                {visit.status}
              </Badge>
            </li>
          ))}
        </ul>
      )}
    </SectionCard>
  );
}
