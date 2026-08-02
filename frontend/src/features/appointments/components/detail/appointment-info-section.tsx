import { AppointmentDetailsCard } from "@/features/appointments/components/appointment-details-card";
import { AppointmentStatusBadge } from "@/features/appointments/components/appointment-status-badge";
import { formatDate, formatTime } from "@/lib/format";
import { getTypeLabel, type AppointmentDetail } from "@/lib/mock/appointments";

export function AppointmentInfoSection({ appointment }: { appointment: AppointmentDetail }) {
  return (
    <AppointmentDetailsCard
      title="Appointment Information"
      fields={[
        { label: "Appointment ID", value: appointment.appointment_number },
        { label: "Status", value: <AppointmentStatusBadge status={appointment.status} /> },
        { label: "Date", value: formatDate(appointment.appointment_date) },
        {
          label: "Time",
          value: `${formatTime(appointment.start_time)} – ${formatTime(appointment.end_time)}`,
        },
        { label: "Visit Type", value: getTypeLabel(appointment.appointment_type) },
        { label: "Booked By", value: appointment.booked_by_name },
      ]}
    />
  );
}
