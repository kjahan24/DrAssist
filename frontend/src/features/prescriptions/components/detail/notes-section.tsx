import { SectionCard } from "@/components/dashboard/section-card";
import { PrescriptionPreview } from "@/features/prescriptions/components/prescription-preview";
import type { PrescriptionDetail } from "@/lib/mock/prescriptions";

export function NotesSection({ prescription }: { prescription: PrescriptionDetail }) {
  return (
    <SectionCard title="Notes">
      <PrescriptionPreview fields={[{ value: prescription.notes }]} />
    </SectionCard>
  );
}
