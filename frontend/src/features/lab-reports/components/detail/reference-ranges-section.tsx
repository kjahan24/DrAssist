import { FlaskConical } from "lucide-react";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import { ReferenceRangeCard } from "@/features/lab-reports/components/reference-range-card";
import type { LabReportDetail } from "@/lib/mock/lab-reports";

export function ReferenceRangesSection({ report }: { report: LabReportDetail }) {
  return (
    <SectionCard
      title="Reference Ranges"
      description="How each result compares to its expected range."
    >
      {report.items.length === 0 ? (
        <EmptyState icon={FlaskConical} title="No results recorded yet" />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {report.items.map((item) => (
            <ReferenceRangeCard key={item.item_id} item={item} />
          ))}
        </div>
      )}
    </SectionCard>
  );
}
