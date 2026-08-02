import Link from "next/link";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { getPatientInitials, type Visit } from "@/lib/mock/visits";

// The combined avatar + name identity cell for the "Patient" column —
// used as `visit-columns.tsx`'s cell renderer and reused as-is in
// `VisitCard` for the mobile layout. Links to the patient's own record.
export function VisitPatientIdentity({
  visit,
}: {
  visit: Pick<Visit, "patient_id" | "patient_name" | "patient_number">;
}) {
  return (
    <Link
      href={`/dashboard/patients/${visit.patient_id}`}
      className="flex items-center gap-3 rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <Avatar className="size-9">
        <AvatarFallback>{getPatientInitials(visit)}</AvatarFallback>
      </Avatar>
      <div className="min-w-0">
        <p className="truncate text-sm font-medium">{visit.patient_name}</p>
        <p className="truncate text-xs text-muted-foreground">{visit.patient_number}</p>
      </div>
    </Link>
  );
}
