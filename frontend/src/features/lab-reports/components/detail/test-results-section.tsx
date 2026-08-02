import { FlaskConical } from "lucide-react";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import { LabResultTable } from "@/features/lab-reports/components/lab-result-table";
import type { LabReportDetail } from "@/lib/mock/lab-reports";

export function TestResultsSection({ report }: { report: LabReportDetail }) {
  return (
    <SectionCard title="Test Results">
      {report.items.length === 0 ? (
        <EmptyState icon={FlaskConical} title="No results recorded yet" />
      ) : (
        <LabResultTable items={report.items} />
      )}
    </SectionCard>
  );
}
