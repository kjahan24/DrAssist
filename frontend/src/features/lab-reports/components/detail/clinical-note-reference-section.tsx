import Link from "next/link";

import { Button } from "@/components/ui/button";
import { LabReportDetailsCard } from "@/features/lab-reports/components/lab-report-details-card";
import type { LabReportDetail } from "@/lib/mock/lab-reports";

export function ClinicalNoteReferenceSection({ report }: { report: LabReportDetail }) {
  return (
    <LabReportDetailsCard
      title="Related Clinical Note"
      actions={
        <Button variant="outline" size="sm" asChild>
          <Link href={`/dashboard/clinical-notes/${report.clinical_note_id}`}>
            View Clinical Note
          </Link>
        </Button>
      }
      fields={[{ label: "Clinical Note ID", value: report.clinical_note_number }]}
    />
  );
}
