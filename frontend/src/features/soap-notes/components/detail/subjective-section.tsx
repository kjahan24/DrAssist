import { SoapNotePreview } from "@/features/soap-notes/components/soap-note-preview";
import { SoapSectionCard } from "@/features/soap-notes/components/soap-section-card";
import type { SOAPNoteDetail } from "@/lib/mock/soap-notes";

export function SubjectiveSection({ note }: { note: SOAPNoteDetail }) {
  return (
    <SoapSectionCard letter="S" title="Subjective">
      <SoapNotePreview fields={[{ value: note.subjective }]} />
    </SoapSectionCard>
  );
}
