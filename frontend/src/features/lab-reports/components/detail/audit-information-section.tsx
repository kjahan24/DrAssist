import { LabReportDetailsCard } from "@/features/lab-reports/components/lab-report-details-card";
import { formatDateTime } from "@/lib/format";
import type { LabReportDetail } from "@/lib/mock/lab-reports";

export function AuditInformationSection({ report }: { report: LabReportDetail }) {
  return (
    <LabReportDetailsCard
      title="Audit Information"
      fields={[
        {
          label: "Created",
          value: `${formatDateTime(report.created_at)} by ${report.created_by_name}`,
        },
        {
          label: "Last Updated",
          value: `${formatDateTime(report.updated_at)} by ${report.updated_by_name}`,
        },
      ]}
    />
  );
}
