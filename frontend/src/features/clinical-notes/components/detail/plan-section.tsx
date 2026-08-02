import { SectionCard } from "@/components/dashboard/section-card";
import { ClinicalNotePreview } from "@/features/clinical-notes/components/clinical-note-preview";
import type { ClinicalNoteDetail } from "@/lib/mock/clinical-notes";

export function PlanSection({ note }: { note: ClinicalNoteDetail }) {
  return (
    <SectionCard title="Plan">
      <ClinicalNotePreview fields={[{ value: note.plan_summary }]} />
    </SectionCard>
  );
}
