import { ClinicalNoteDetailsCard } from "@/features/clinical-notes/components/clinical-note-details-card";
import type { ClinicalNoteDetail } from "@/lib/mock/clinical-notes";

export function DoctorSummarySection({ note }: { note: ClinicalNoteDetail }) {
  return (
    <ClinicalNoteDetailsCard
      title="Doctor Summary"
      fields={[{ label: "Doctor", value: note.doctor_name }]}
    />
  );
}
