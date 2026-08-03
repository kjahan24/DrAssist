import Link from "next/link";

import { Button } from "@/components/ui/button";
import { PrescriptionDetailsCard } from "@/features/prescriptions/components/prescription-details-card";
import { formatDate } from "@/lib/format";
import type { PrescriptionDetail } from "@/lib/mock/prescriptions";

export function VisitSummarySection({ prescription }: { prescription: PrescriptionDetail }) {
  return (
    <PrescriptionDetailsCard
      title="Visit Summary"
      actions={
        <Button variant="outline" size="sm" asChild>
          <Link href={`/dashboard/visits/${prescription.visit_id}`}>View Visit</Link>
        </Button>
      }
      fields={[
        { label: "Visit ID", value: prescription.visit_number },
        { label: "Issued", value: formatDate(prescription.prescription_date) },
      ]}
    />
  );
}
