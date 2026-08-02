import Link from "next/link";

import { Button } from "@/components/ui/button";
import { SoapNoteDetailsCard } from "@/features/soap-notes/components/soap-note-details-card";
import type { SOAPNoteDetail } from "@/lib/mock/soap-notes";

export function PatientSummarySection({ note }: { note: SOAPNoteDetail }) {
  return (
    <SoapNoteDetailsCard
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
