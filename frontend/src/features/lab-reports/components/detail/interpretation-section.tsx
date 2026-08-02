import { SectionCard } from "@/components/dashboard/section-card";
import { LabReportPreview } from "@/features/lab-reports/components/lab-report-preview";
import type { LabReportDetail } from "@/lib/mock/lab-reports";

export function InterpretationSection({ report }: { report: LabReportDetail }) {
  return (
    <SectionCard
      title="Interpretation"
      description="Overall clinical interpretation of this report."
    >
      <LabReportPreview fields={[{ value: report.interpretation }]} />
    </SectionCard>
  );
}
