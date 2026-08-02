import Link from "next/link";

import { PatientRow } from "@/features/patients/components/patient-row";
import { PatientStatusBadge } from "@/features/patients/components/patient-status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { formatDate } from "@/lib/format";
import { getAge, type Patient } from "@/lib/mock/patients";

// The mobile-breakpoint counterpart to `PatientTable` — a data table
// doesn't work well on narrow screens, so `PatientListContent` shows this
// instead, below `md`.
export function PatientCard({ patient }: { patient: Patient }) {
  return (
    <Card>
      <CardContent className="space-y-3 pt-6">
        <div className="flex items-center justify-between gap-2">
          <PatientRow patient={patient} />
          <PatientStatusBadge status={patient.status} />
        </div>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <div>
            <dt className="text-xs text-muted-foreground">Age / Gender</dt>
            <dd className="capitalize">
              {getAge(patient.date_of_birth)} yrs · {patient.gender}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Blood Group</dt>
            <dd>{patient.blood_group}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Phone</dt>
            <dd className="truncate">{patient.phone}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Last Visit</dt>
            <dd>{patient.last_visit_date ? formatDate(patient.last_visit_date) : "—"}</dd>
          </div>
        </dl>
        <div className="flex gap-2 pt-1">
          <Button variant="outline" size="sm" className="flex-1" asChild>
            <Link href={`/dashboard/patients/${patient.patient_id}`}>View</Link>
          </Button>
          <Button variant="outline" size="sm" className="flex-1" asChild>
            <Link href={`/dashboard/patients/${patient.patient_id}/edit`}>Edit</Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
