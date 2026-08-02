import { SoapNotePreview } from "@/features/soap-notes/components/soap-note-preview";
import { SoapSectionCard } from "@/features/soap-notes/components/soap-section-card";
import type { SOAPNoteDetail } from "@/lib/mock/soap-notes";

export function PlanSection({ note }: { note: SOAPNoteDetail }) {
  return (
    <SoapSectionCard letter="P" title="Plan">
      <SoapNotePreview fields={[{ value: note.plan }]} />
    </SoapSectionCard>
  );
}
