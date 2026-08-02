import Link from "next/link";
import { Pencil } from "lucide-react";

import { PatientStatusBadge } from "@/features/patients/components/patient-status-badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { getAge, getFullName, getInitials, type PatientDetail } from "@/lib/mock/patients";

// The detail page's only heading — the page's real <h1>.
export function PatientProfileHeader({ patient }: { patient: PatientDetail }) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-center gap-4">
        <Avatar className="size-16">
          <AvatarFallback className="text-lg">{getInitials(patient)}</AvatarFallback>
        </Avatar>
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-semibold tracking-tight">{getFullName(patient)}</h1>
            <PatientStatusBadge status={patient.status} />
          </div>
          <p className="text-sm text-muted-foreground">
            {patient.patient_number} · {getAge(patient.date_of_birth)} yrs ·{" "}
            <span className="capitalize">{patient.gender}</span> · {patient.blood_group}
          </p>
        </div>
      </div>
      <Button asChild>
        <Link href={`/dashboard/patients/${patient.patient_id}/edit`}>
          <Pencil className="size-4" />
          Edit Patient
        </Link>
      </Button>
    </div>
  );
}
