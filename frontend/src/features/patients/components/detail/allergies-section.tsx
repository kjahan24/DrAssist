import { ShieldAlert } from "lucide-react";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Badge } from "@/components/ui/badge";
import type { Allergy } from "@/lib/mock/patients";

const SEVERITY_VARIANT: Record<Allergy["severity"], "secondary" | "default" | "destructive"> = {
  mild: "secondary",
  moderate: "default",
  severe: "destructive",
};

export function AllergiesSection({ allergies }: { allergies: Allergy[] }) {
  return (
    <SectionCard title="Allergies" description="Known allergies and reactions.">
      {allergies.length === 0 ? (
        <EmptyState icon={ShieldAlert} title="No known allergies" />
      ) : (
        <ul className="space-y-3">
          {allergies.map((allergy) => (
            <li
              key={allergy.allergy_id}
              className="flex items-start justify-between gap-3 rounded-lg border p-3"
            >
              <div className="space-y-0.5">
                <p className="text-sm font-medium">{allergy.allergen_name}</p>
                <p className="text-xs capitalize text-muted-foreground">
                  {allergy.allergy_type} · {allergy.reaction}
                </p>
              </div>
              <Badge variant={SEVERITY_VARIANT[allergy.severity]} className="shrink-0 capitalize">
                {allergy.severity}
              </Badge>
            </li>
          ))}
        </ul>
      )}
    </SectionCard>
  );
}
