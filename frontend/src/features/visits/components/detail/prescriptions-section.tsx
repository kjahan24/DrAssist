import { Pill } from "lucide-react";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/format";
import type { VisitDetail } from "@/lib/mock/visits";

export function PrescriptionsSection({ visit }: { visit: VisitDetail }) {
  const prescription = visit.prescription;

  return (
    <SectionCard title="Prescriptions">
      {!prescription ? (
        <EmptyState icon={Pill} title="No prescriptions issued" />
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="text-sm font-medium">{prescription.prescription_number}</p>
              <p className="text-xs text-muted-foreground">
                {formatDate(prescription.prescription_date)}
              </p>
            </div>
            <Badge variant={prescription.status === "final" ? "default" : "outline"}>
              {prescription.status === "final" ? "Final" : "Draft"}
            </Badge>
          </div>
          <ul className="divide-y">
            {prescription.items.map((item) => (
              <li key={item.item_id} className="space-y-1 py-3 first:pt-0 last:pb-0">
                <p className="text-sm font-medium">
                  {item.medication_name} · {item.strength}
                </p>
                <p className="text-xs text-muted-foreground">
                  {item.dosage} {item.dosage_unit} · {item.frequency} · {item.route} ·{" "}
                  {item.duration} {item.duration_unit} · Qty {item.quantity}
                </p>
                {item.instructions && <p className="text-sm">{item.instructions}</p>}
              </li>
            ))}
          </ul>
          {prescription.notes && (
            <p className="text-sm text-muted-foreground">{prescription.notes}</p>
          )}
        </div>
      )}
    </SectionCard>
  );
}
