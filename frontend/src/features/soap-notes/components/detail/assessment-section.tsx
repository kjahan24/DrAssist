import { SoapNotePreview } from "@/features/soap-notes/components/soap-note-preview";
import { SoapSectionCard } from "@/features/soap-notes/components/soap-section-card";
import type { SOAPNoteDetail } from "@/lib/mock/soap-notes";

export function AssessmentSection({ note }: { note: SOAPNoteDetail }) {
  return (
    <SoapSectionCard letter="A" title="Assessment">
      <SoapNotePreview fields={[{ value: note.assessment }]} />
    </SoapSectionCard>
  );
}
