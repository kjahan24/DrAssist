import Link from "next/link";

import { Button } from "@/components/ui/button";
import { DocumentDetailsCard } from "@/features/documents/components/document-details-card";
import type { MedicalDocumentDetail } from "@/lib/mock/documents";

export function PatientSummarySection({ document }: { document: MedicalDocumentDetail }) {
  return (
    <DocumentDetailsCard
      title="Patient Summary"
      actions={
        <Button variant="outline" size="sm" asChild>
          <Link href={`/dashboard/patients/${document.patient_id}`}>View Record</Link>
        </Button>
      }
      fields={[
        { label: "Patient", value: document.patient_name },
        { label: "Patient ID", value: document.patient_number },
      ]}
    />
  );
}
