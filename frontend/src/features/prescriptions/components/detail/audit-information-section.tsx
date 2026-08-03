import { PrescriptionDetailsCard } from "@/features/prescriptions/components/prescription-details-card";
import { formatDateTime } from "@/lib/format";
import type { PrescriptionDetail } from "@/lib/mock/prescriptions";

export function AuditInformationSection({ prescription }: { prescription: PrescriptionDetail }) {
  return (
    <PrescriptionDetailsCard
      title="Audit Information"
      fields={[
        {
          label: "Created",
          value: `${formatDateTime(prescription.created_at)} by ${prescription.created_by_name}`,
        },
        {
          label: "Last Updated",
          value: `${formatDateTime(prescription.updated_at)} by ${prescription.updated_by_name}`,
        },
      ]}
    />
  );
}
