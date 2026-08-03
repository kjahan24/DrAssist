import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { PrescriptionPatientIdentity } from "@/features/prescriptions/components/prescription-patient-identity";
import { PrescriptionStatusBadge } from "@/features/prescriptions/components/prescription-status-badge";
import { formatDate } from "@/lib/format";
import { isPrescriptionEditable, type Prescription } from "@/lib/mock/prescriptions";

// The mobile-breakpoint counterpart to `PrescriptionTable` — shown
// below `md`, where `PrescriptionListContent` hides the data table.
export function PrescriptionCard({ prescription }: { prescription: Prescription }) {
  return (
    <Card>
      <CardContent className="space-y-3 pt-6">
        <div className="flex items-center justify-between gap-2">
          <PrescriptionPatientIdentity prescription={prescription} />
          <PrescriptionStatusBadge status={prescription.status} />
        </div>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <div>
            <dt className="text-xs text-muted-foreground">Doctor</dt>
            <dd className="truncate">{prescription.doctor_name}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Visit</dt>
            <dd className="truncate">{prescription.visit_number}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Issued</dt>
            <dd>{formatDate(prescription.prescription_date)}</dd>
          </div>
        </dl>
        <div className="flex gap-2 pt-1">
          <Button variant="outline" size="sm" className="flex-1" asChild>
            <Link href={`/dashboard/prescriptions/${prescription.prescription_id}`}>View</Link>
          </Button>
          {isPrescriptionEditable(prescription.status) && (
            <Button variant="outline" size="sm" className="flex-1" asChild>
              <Link href={`/dashboard/prescriptions/${prescription.prescription_id}/edit`}>
                Edit
              </Link>
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
