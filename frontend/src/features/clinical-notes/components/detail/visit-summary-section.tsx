import Link from "next/link";

import { Button } from "@/components/ui/button";
import { ClinicalNoteDetailsCard } from "@/features/clinical-notes/components/clinical-note-details-card";
import { formatDateTime } from "@/lib/format";
import { getClinicalNoteTypeLabel, type ClinicalNoteDetail } from "@/lib/mock/clinical-notes";

export function VisitSummarySection({ note }: { note: ClinicalNoteDetail }) {
  return (
    <ClinicalNoteDetailsCard
      title="Visit Summary"
      actions={
        <Button variant="outline" size="sm" asChild>
          <Link href={`/dashboard/visits/${note.visit_id}`}>View Visit</Link>
        </Button>
      }
      fields={[
        { label: "Visit ID", value: note.visit_number },
        { label: "Encounter Date", value: formatDateTime(note.encounter_datetime) },
        { label: "Note Type", value: getClinicalNoteTypeLabel(note.note_type) },
      ]}
    />
  );
}
