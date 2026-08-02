import { LabReportDetailsCard } from "@/features/lab-reports/components/lab-report-details-card";
import { LabReportStatusBadge } from "@/features/lab-reports/components/lab-report-status-badge";
import { formatDateTime } from "@/lib/format";
import { getLabReportCategoryLabel, type LabReportDetail } from "@/lib/mock/lab-reports";

const PRIORITY_LABEL: Record<LabReportDetail["priority"], string> = {
  routine: "Routine",
  urgent: "Urgent",
  stat: "STAT",
};

export function ReportInformationSection({ report }: { report: LabReportDetail }) {
  return (
    <LabReportDetailsCard
      title="Report Information"
      fields={[
        { label: "Report ID", value: report.report_number },
        { label: "Status", value: <LabReportStatusBadge status={report.status} /> },
        { label: "Category", value: getLabReportCategoryLabel(report.category) },
        { label: "Priority", value: PRIORITY_LABEL[report.priority] },
        { label: "Ordered At", value: formatDateTime(report.ordered_at) },
        {
          label: "Collected At",
          value: report.collected_at ? formatDateTime(report.collected_at) : null,
        },
        {
          label: "Reported At",
          value: report.reported_at ? formatDateTime(report.reported_at) : null,
        },
        { label: "Laboratory", value: report.laboratory_name },
        { label: "Clinical Information", value: report.clinical_information },
      ]}
    />
  );
}
