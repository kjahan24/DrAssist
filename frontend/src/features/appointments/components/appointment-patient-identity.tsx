import Link from "next/link";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { getPatientInitials, type Appointment } from "@/lib/mock/appointments";

// The combined avatar + name identity cell for the "Patient" column —
// used as `appointment-columns.tsx`'s cell renderer and reused as-is in
// `AppointmentCard` for the mobile layout. Links to the patient's own
// record (not the appointment) since that's what a clinician scanning
// this column is usually trying to reach.
export function AppointmentPatientIdentity({
  appointment,
}: {
  appointment: Pick<Appointment, "patient_id" | "patient_name" | "patient_number">;
}) {
  return (
    <Link
      href={`/dashboard/patients/${appointment.patient_id}`}
      className="flex items-center gap-3 rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <Avatar className="size-9">
        <AvatarFallback>{getPatientInitials(appointment)}</AvatarFallback>
      </Avatar>
      <div className="min-w-0">
        <p className="truncate text-sm font-medium">{appointment.patient_name}</p>
        <p className="truncate text-xs text-muted-foreground">{appointment.patient_number}</p>
      </div>
    </Link>
  );
}
