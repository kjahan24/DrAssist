import Link from "next/link";

import { Button } from "@/components/ui/button";
import { LabReportDetailsCard } from "@/features/lab-reports/components/lab-report-details-card";
import type { LabReportDetail } from "@/lib/mock/lab-reports";

export function VisitSummarySection({ report }: { report: LabReportDetail }) {
  return (
    <LabReportDetailsCard
      title="Visit Summary"
      actions={
        <Button variant="outline" size="sm" asChild>
          <Link href={`/dashboard/visits/${report.visit_id}`}>View Visit</Link>
        </Button>
      }
      fields={[{ label: "Visit ID", value: report.visit_number }]}
    />
  );
}
