import { SectionCard } from "@/components/dashboard/section-card";
import type { AppointmentDetail } from "@/lib/mock/appointments";

export function ReasonForVisitSection({ appointment }: { appointment: AppointmentDetail }) {
  return (
    <SectionCard title="Reason for Visit">
      <p className="text-sm">
        {appointment.reason_for_visit || (
          <span className="text-muted-foreground">Not provided.</span>
        )}
      </p>
    </SectionCard>
  );
}
