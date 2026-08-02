import Link from "next/link";

import { Button } from "@/components/ui/button";
import { AppointmentDetailsCard } from "@/features/appointments/components/appointment-details-card";
import type { AppointmentDetail } from "@/lib/mock/appointments";

export function PatientSummarySection({ appointment }: { appointment: AppointmentDetail }) {
  return (
    <AppointmentDetailsCard
      title="Patient Summary"
      actions={
        <Button variant="outline" size="sm" asChild>
          <Link href={`/dashboard/patients/${appointment.patient_id}`}>View Record</Link>
        </Button>
      }
      fields={[
        { label: "Patient", value: appointment.patient_name },
        { label: "Patient ID", value: appointment.patient_number },
      ]}
    />
  );
}
