import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { AppointmentPatientIdentity } from "@/features/appointments/components/appointment-patient-identity";
import { AppointmentStatusBadge } from "@/features/appointments/components/appointment-status-badge";
import { formatDate, formatTime } from "@/lib/format";
import { getTypeLabel, type Appointment } from "@/lib/mock/appointments";

// The mobile-breakpoint counterpart to `AppointmentTable` — shown below
// `md`, where `AppointmentListContent` hides the data table.
export function AppointmentCard({ appointment }: { appointment: Appointment }) {
  return (
    <Card>
      <CardContent className="space-y-3 pt-6">
        <div className="flex items-center justify-between gap-2">
          <AppointmentPatientIdentity appointment={appointment} />
          <AppointmentStatusBadge status={appointment.status} />
        </div>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <div>
            <dt className="text-xs text-muted-foreground">Doctor</dt>
            <dd className="truncate">{appointment.doctor_name}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Department</dt>
            <dd className="truncate">{appointment.department}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Date &amp; Time</dt>
            <dd>
              {formatDate(appointment.appointment_date)} · {formatTime(appointment.start_time)}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Visit Type</dt>
            <dd>{getTypeLabel(appointment.appointment_type)}</dd>
          </div>
        </dl>
        <div className="flex gap-2 pt-1">
          <Button variant="outline" size="sm" className="flex-1" asChild>
            <Link href={`/dashboard/appointments/${appointment.appointment_id}`}>View</Link>
          </Button>
          <Button variant="outline" size="sm" className="flex-1" asChild>
            <Link href={`/dashboard/appointments/${appointment.appointment_id}/edit`}>Edit</Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
