import Link from "next/link";

import { Button } from "@/components/ui/button";
import { SoapNoteDetailsCard } from "@/features/soap-notes/components/soap-note-details-card";
import type { SOAPNoteDetail } from "@/lib/mock/soap-notes";

export function ClinicalNoteReferenceSection({ note }: { note: SOAPNoteDetail }) {
  return (
    <SoapNoteDetailsCard
      title="Clinical Note Reference"
      description="This SOAP note is a structured section of its parent clinical note."
      actions={
        <Button variant="outline" size="sm" asChild>
          <Link href={`/dashboard/clinical-notes/${note.clinical_note_id}`}>
            View Clinical Note
          </Link>
        </Button>
      }
      fields={[{ label: "Clinical Note ID", value: note.clinical_note_number }]}
    />
  );
}
