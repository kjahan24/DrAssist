import { SoapNotePreview } from "@/features/soap-notes/components/soap-note-preview";
import { SoapSectionCard } from "@/features/soap-notes/components/soap-section-card";
import type { SOAPNoteDetail } from "@/lib/mock/soap-notes";

export function ObjectiveSection({ note }: { note: SOAPNoteDetail }) {
  return (
    <SoapSectionCard letter="O" title="Objective">
      <SoapNotePreview fields={[{ value: note.objective }]} />
    </SoapSectionCard>
  );
}
