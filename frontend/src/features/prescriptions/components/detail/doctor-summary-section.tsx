import { PrescriptionDetailsCard } from "@/features/prescriptions/components/prescription-details-card";
import type { PrescriptionDetail } from "@/lib/mock/prescriptions";

export function DoctorSummarySection({ prescription }: { prescription: PrescriptionDetail }) {
  return (
    <PrescriptionDetailsCard
      title="Doctor Summary"
      fields={[{ label: "Prescribed By", value: prescription.doctor_name }]}
    />
  );
}
