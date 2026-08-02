import { SectionCard } from "@/components/dashboard/section-card";
import { ClinicalNotePreview } from "@/features/clinical-notes/components/clinical-note-preview";
import type { ClinicalNoteDetail } from "@/lib/mock/clinical-notes";

export function AssessmentSection({ note }: { note: ClinicalNoteDetail }) {
  return (
    <SectionCard title="Assessment">
      <ClinicalNotePreview fields={[{ value: note.assessment_summary }]} />
    </SectionCard>
  );
}
