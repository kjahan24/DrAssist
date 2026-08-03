import Link from "next/link";

import { Button } from "@/components/ui/button";
import { PrescriptionDetailsCard } from "@/features/prescriptions/components/prescription-details-card";
import type { PrescriptionDetail } from "@/lib/mock/prescriptions";

export function ClinicalNoteReferenceSection({
  prescription,
}: {
  prescription: PrescriptionDetail;
}) {
  return (
    <PrescriptionDetailsCard
      title="Related Clinical Note"
      actions={
        <Button variant="outline" size="sm" asChild>
          <Link href={`/dashboard/clinical-notes/${prescription.clinical_note_id}`}>
            View Clinical Note
          </Link>
        </Button>
      }
      fields={[{ label: "Clinical Note ID", value: prescription.clinical_note_number }]}
    />
  );
}
