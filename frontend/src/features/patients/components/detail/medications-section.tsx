import { Pill } from "lucide-react";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/format";
import type { Medication } from "@/lib/mock/patients";

export function MedicationsSection({ medications }: { medications: Medication[] }) {
  return (
    <SectionCard title="Medications" description="Current and past medications.">
      {medications.length === 0 ? (
        <EmptyState icon={Pill} title="No medications on file" />
      ) : (
        <ul className="space-y-3">
          {medications.map((medication) => (
            <li
              key={medication.medication_id}
              className="flex items-start justify-between gap-3 rounded-lg border p-3"
            >
              <div className="space-y-0.5">
                <p className="text-sm font-medium">{medication.medication_name}</p>
                <p className="text-xs text-muted-foreground">
                  {medication.dosage}
                  {medication.dosage_unit} · {medication.frequency} · {medication.route}
                </p>
                <p className="text-xs text-muted-foreground">
                  Since {formatDate(medication.start_date)}
                </p>
              </div>
              <Badge variant={medication.is_current ? "default" : "secondary"} className="shrink-0">
                {medication.is_current ? "Current" : "Past"}
              </Badge>
            </li>
          ))}
        </ul>
      )}
    </SectionCard>
  );
}
