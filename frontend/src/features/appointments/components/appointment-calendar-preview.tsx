import Link from "next/link";

import { CardSkeleton } from "@/components/shared/states/card-skeleton";
import { AppointmentStatusBadge } from "@/features/appointments/components/appointment-status-badge";
import { formatDate, formatTime } from "@/lib/format";
import { getTypeLabel, type Appointment } from "@/lib/mock/appointments";

interface AppointmentCalendarPreviewProps {
  appointments: Appointment[];
  isLoading?: boolean;
}

function groupByDate(appointments: Appointment[]): [string, Appointment[]][] {
  const groups = new Map<string, Appointment[]>();
  for (const appointment of appointments) {
    const existing = groups.get(appointment.appointment_date);
    if (existing) {
      existing.push(appointment);
    } else {
      groups.set(appointment.appointment_date, [appointment]);
    }
  }
  return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b));
}

// A lightweight day-by-day agenda, not a full interactive month grid — the
// project has no calendar-grid primitive (no `react-day-picker`/
// `calendar.tsx`) and adding one purely for a list-page preview would be
// scope creep. Groups whatever page of filtered/sorted appointments the
// caller passed in (`AppointmentListContent` requests a larger page while
// this view is active) by date, chronologically.
export function AppointmentCalendarPreview({
  appointments,
  isLoading,
}: AppointmentCalendarPreviewProps) {
  if (isLoading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 3 }).map((_, index) => (
          <CardSkeleton key={index} />
        ))}
      </div>
    );
  }

  const groups = groupByDate(appointments);

  return (
    <div className="space-y-6">
      {groups.map(([date, dayAppointments]) => (
        <div key={date}>
          <h2 className="mb-3 text-sm font-semibold text-muted-foreground">
            {formatDate(date, "EEEE, MMM d, yyyy")}
          </h2>
          <ul className="space-y-2">
            {dayAppointments.map((appointment) => (
              <li key={appointment.appointment_id}>
                <Link
                  href={`/dashboard/appointments/${appointment.appointment_id}`}
                  className="flex items-center justify-between gap-3 rounded-md border p-3 hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <span className="w-20 shrink-0 text-sm font-medium tabular-nums">
                      {formatTime(appointment.start_time)}
                    </span>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{appointment.patient_name}</p>
                      <p className="truncate text-xs text-muted-foreground">
                        {appointment.doctor_name} · {getTypeLabel(appointment.appointment_type)}
                      </p>
                    </div>
                  </div>
                  <AppointmentStatusBadge status={appointment.status} />
                </Link>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
