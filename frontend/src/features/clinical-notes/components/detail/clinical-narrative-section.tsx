import { SectionCard } from "@/components/dashboard/section-card";
import { ClinicalNotePreview } from "@/features/clinical-notes/components/clinical-note-preview";
import type { ClinicalNoteDetail } from "@/lib/mock/clinical-notes";

export function ClinicalNarrativeSection({ note }: { note: ClinicalNoteDetail }) {
  return (
    <SectionCard title="Clinical Narrative">
      <ClinicalNotePreview
        fields={[
          { label: "Chief Complaint", value: note.chief_complaint_summary },
          { label: "History of Present Illness", value: note.history_summary },
          { label: "Examination Findings", value: note.examination_summary },
        ]}
      />
    </SectionCard>
  );
}
