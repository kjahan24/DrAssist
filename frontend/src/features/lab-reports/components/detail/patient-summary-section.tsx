import Link from "next/link";

import { Button } from "@/components/ui/button";
import { LabReportDetailsCard } from "@/features/lab-reports/components/lab-report-details-card";
import type { LabReportDetail } from "@/lib/mock/lab-reports";

export function PatientSummarySection({ report }: { report: LabReportDetail }) {
  return (
    <LabReportDetailsCard
      title="Patient Summary"
      actions={
        <Button variant="outline" size="sm" asChild>
          <Link href={`/dashboard/patients/${report.patient_id}`}>View Record</Link>
        </Button>
      }
      fields={[
        { label: "Patient", value: report.patient_name },
        { label: "Patient ID", value: report.patient_number },
      ]}
    />
  );
}
