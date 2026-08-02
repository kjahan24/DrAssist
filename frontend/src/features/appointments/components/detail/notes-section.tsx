import { SectionCard } from "@/components/dashboard/section-card";
import type { AppointmentDetail } from "@/lib/mock/appointments";

export function NotesSection({ appointment }: { appointment: AppointmentDetail }) {
  return (
    <SectionCard title="Notes">
      <p className="whitespace-pre-wrap text-sm">
        {appointment.notes || <span className="text-muted-foreground">No notes on file.</span>}
      </p>
    </SectionCard>
  );
}
