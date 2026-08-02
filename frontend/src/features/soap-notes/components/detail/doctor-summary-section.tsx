import { SoapNoteDetailsCard } from "@/features/soap-notes/components/soap-note-details-card";
import type { SOAPNoteDetail } from "@/lib/mock/soap-notes";

export function DoctorSummarySection({ note }: { note: SOAPNoteDetail }) {
  return (
    <SoapNoteDetailsCard
      title="Doctor Summary"
      fields={[{ label: "Doctor", value: note.doctor_name }]}
    />
  );
}
