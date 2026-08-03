import Link from "next/link";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import type { LabReport } from "@/lib/mock/lab-reports";
import { getInitials } from "@/lib/utils";

// The combined avatar + name identity cell for the "Patient" column —
// used as `lab-report-columns.tsx`'s cell renderer and reused as-is in
// `LabReportCard` for the mobile layout. Links to the patient's own
// record.
export function LabReportPatientIdentity({
  report,
}: {
  report: Pick<LabReport, "patient_id" | "patient_name" | "patient_number">;
}) {
  return (
    <Link
      href={`/dashboard/patients/${report.patient_id}`}
      className="flex items-center gap-3 rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <Avatar className="size-9">
        <AvatarFallback>{getInitials(report.patient_name)}</AvatarFallback>
      </Avatar>
      <div className="min-w-0">
        <p className="truncate text-sm font-medium">{report.patient_name}</p>
        <p className="truncate text-xs text-muted-foreground">{report.patient_number}</p>
      </div>
    </Link>
  );
}
