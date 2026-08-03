import Link from "next/link";

import { Button } from "@/components/ui/button";
import { PrescriptionDetailsCard } from "@/features/prescriptions/components/prescription-details-card";
import type { PrescriptionDetail } from "@/lib/mock/prescriptions";

export function PatientSummarySection({ prescription }: { prescription: PrescriptionDetail }) {
  return (
    <PrescriptionDetailsCard
      title="Patient Summary"
      actions={
        <Button variant="outline" size="sm" asChild>
          <Link href={`/dashboard/patients/${prescription.patient_id}`}>View Record</Link>
        </Button>
      }
      fields={[
        { label: "Patient", value: prescription.patient_name },
        { label: "Patient ID", value: prescription.patient_number },
      ]}
    />
  );
}
