import { AppointmentDetailsCard } from "@/features/appointments/components/appointment-details-card";
import type { AppointmentDetail } from "@/lib/mock/appointments";

export function DoctorInfoSection({ appointment }: { appointment: AppointmentDetail }) {
  return (
    <AppointmentDetailsCard
      title="Doctor Information"
      fields={[
        { label: "Doctor", value: appointment.doctor_name },
        { label: "Department", value: appointment.department },
      ]}
    />
  );
}
