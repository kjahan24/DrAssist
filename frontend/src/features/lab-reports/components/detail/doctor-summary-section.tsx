import { LabReportDetailsCard } from "@/features/lab-reports/components/lab-report-details-card";
import type { LabReportDetail } from "@/lib/mock/lab-reports";

export function DoctorSummarySection({ report }: { report: LabReportDetail }) {
  return (
    <LabReportDetailsCard
      title="Doctor Summary"
      fields={[{ label: "Ordered By", value: report.doctor_name }]}
    />
  );
}
