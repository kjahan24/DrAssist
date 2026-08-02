import Link from "next/link";

import { Button } from "@/components/ui/button";
import { ClinicalNoteDetailsCard } from "@/features/clinical-notes/components/clinical-note-details-card";
import type { ClinicalNoteDetail } from "@/lib/mock/clinical-notes";

export function PatientSummarySection({ note }: { note: ClinicalNoteDetail }) {
  return (
    <ClinicalNoteDetailsCard
      title="Patient Summary"
      actions={
        <Button variant="outline" size="sm" asChild>
          <Link href={`/dashboard/patients/${note.patient_id}`}>View Record</Link>
        </Button>
      }
      fields={[
        { label: "Patient", value: note.patient_name },
        { label: "Patient ID", value: note.patient_number },
      ]}
    />
  );
}
