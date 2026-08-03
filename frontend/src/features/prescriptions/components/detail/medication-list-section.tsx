import { Pill } from "lucide-react";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import { MedicationCard } from "@/features/prescriptions/components/medication-card";
import type { PrescriptionDetail } from "@/lib/mock/prescriptions";

export function MedicationListSection({ prescription }: { prescription: PrescriptionDetail }) {
  return (
    <SectionCard title="Medication List">
      {prescription.items.length === 0 ? (
        <EmptyState icon={Pill} title="No medications on this prescription yet" />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {prescription.items.map((item) => (
            <MedicationCard key={item.prescription_item_id} item={item} />
          ))}
        </div>
      )}
    </SectionCard>
  );
}
