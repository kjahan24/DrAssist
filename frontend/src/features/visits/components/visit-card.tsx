import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { VisitPatientIdentity } from "@/features/visits/components/visit-patient-identity";
import { VisitStatusBadge } from "@/features/visits/components/visit-status-badge";
import { formatDate } from "@/lib/format";
import { getVisitTypeLabel, type Visit } from "@/lib/mock/visits";

// The mobile-breakpoint counterpart to `VisitTable` — shown below `md`,
// where `VisitListContent` hides the data table.
export function VisitCard({ visit }: { visit: Visit }) {
  return (
    <Card>
      <CardContent className="space-y-3 pt-6">
        <div className="flex items-center justify-between gap-2">
          <VisitPatientIdentity visit={visit} />
          <VisitStatusBadge status={visit.visit_status} />
        </div>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <div>
            <dt className="text-xs text-muted-foreground">Doctor</dt>
            <dd className="truncate">{visit.doctor_name}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Visit Date</dt>
            <dd>{formatDate(visit.visit_date)}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Visit Type</dt>
            <dd>{getVisitTypeLabel(visit.visit_type)}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Chief Complaint</dt>
            <dd className="truncate">{visit.chief_complaint_summary || "—"}</dd>
          </div>
        </dl>
        <div className="flex gap-2 pt-1">
          <Button variant="outline" size="sm" className="flex-1" asChild>
            <Link href={`/dashboard/visits/${visit.visit_id}`}>View</Link>
          </Button>
          <Button variant="outline" size="sm" className="flex-1" asChild>
            <Link href={`/dashboard/visits/${visit.visit_id}/edit`}>Edit</Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
