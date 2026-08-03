import Link from "next/link";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import type { Prescription } from "@/lib/mock/prescriptions";
import { getInitials } from "@/lib/utils";

// The combined avatar + name identity cell for the "Patient" column —
// used as `prescription-columns.tsx`'s cell renderer and reused as-is
// in `PrescriptionCard` for the mobile layout. Links to the patient's
// own record.
export function PrescriptionPatientIdentity({
  prescription,
}: {
  prescription: Pick<Prescription, "patient_id" | "patient_name" | "patient_number">;
}) {
  return (
    <Link
      href={`/dashboard/patients/${prescription.patient_id}`}
      className="flex items-center gap-3 rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <Avatar className="size-9">
        <AvatarFallback>{getInitials(prescription.patient_name)}</AvatarFallback>
      </Avatar>
      <div className="min-w-0">
        <p className="truncate text-sm font-medium">{prescription.patient_name}</p>
        <p className="truncate text-xs text-muted-foreground">{prescription.patient_number}</p>
      </div>
    </Link>
  );
}
