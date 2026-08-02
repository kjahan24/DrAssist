import Link from "next/link";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { getFullName, getInitials, type Patient } from "@/lib/mock/patients";

// The combined avatar + name identity cell — used as the "Patient"
// column's cell renderer in `patient-columns.tsx` and reused as-is inside
// `PatientCard` for the mobile layout, so the same identity presentation
// never has to be built twice.
export function PatientRow({
  patient,
}: {
  patient: Pick<Patient, "patient_id" | "first_name" | "last_name">;
}) {
  return (
    <Link
      href={`/dashboard/patients/${patient.patient_id}`}
      className="flex items-center gap-3 rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <Avatar className="size-9">
        <AvatarFallback>{getInitials(patient)}</AvatarFallback>
      </Avatar>
      <span className="truncate text-sm font-medium">{getFullName(patient)}</span>
    </Link>
  );
}
