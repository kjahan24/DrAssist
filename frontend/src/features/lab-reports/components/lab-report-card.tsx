import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { LabReportPatientIdentity } from "@/features/lab-reports/components/lab-report-patient-identity";
import { LabReportStatusBadge } from "@/features/lab-reports/components/lab-report-status-badge";
import { formatDate } from "@/lib/format";
import {
  getLabReportCategoryLabel,
  isLabReportEditable,
  type LabReport,
} from "@/lib/mock/lab-reports";

// The mobile-breakpoint counterpart to `LabReportTable` — shown below
// `md`, where `LabReportListContent` hides the data table.
export function LabReportCard({ report }: { report: LabReport }) {
  return (
    <Card>
      <CardContent className="space-y-3 pt-6">
        <div className="flex items-center justify-between gap-2">
          <LabReportPatientIdentity report={report} />
          <LabReportStatusBadge status={report.status} />
        </div>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <div>
            <dt className="text-xs text-muted-foreground">Test</dt>
            <dd className="truncate">{report.test_summary}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Category</dt>
            <dd>{getLabReportCategoryLabel(report.category)}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Ordered By</dt>
            <dd className="truncate">{report.doctor_name}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Collected</dt>
            <dd>{report.collected_at ? formatDate(report.collected_at) : "—"}</dd>
          </div>
        </dl>
        <div className="flex gap-2 pt-1">
          <Button variant="outline" size="sm" className="flex-1" asChild>
            <Link href={`/dashboard/lab-reports/${report.lab_report_id}`}>View</Link>
          </Button>
          {isLabReportEditable(report.status) && (
            <Button variant="outline" size="sm" className="flex-1" asChild>
              <Link href={`/dashboard/lab-reports/${report.lab_report_id}/edit`}>Edit</Link>
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
