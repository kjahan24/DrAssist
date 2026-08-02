import { Activity } from "lucide-react";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/format";
import type { MedicalCondition } from "@/lib/mock/patients";

export function ConditionsSection({ conditions }: { conditions: MedicalCondition[] }) {
  return (
    <SectionCard title="Medical Conditions" description="Diagnosed conditions.">
      {conditions.length === 0 ? (
        <EmptyState icon={Activity} title="No medical conditions on file" />
      ) : (
        <ul className="space-y-3">
          {conditions.map((condition) => (
            <li
              key={condition.condition_id}
              className="flex items-start justify-between gap-3 rounded-lg border p-3"
            >
              <div className="space-y-0.5">
                <p className="text-sm font-medium">{condition.condition_name}</p>
                <p className="text-xs text-muted-foreground">
                  Diagnosed {formatDate(condition.diagnosis_date)}
                  {condition.icd10_code ? ` · ${condition.icd10_code}` : ""}
                </p>
              </div>
              <Badge
                variant={condition.is_chronic ? "secondary" : "outline"}
                className="shrink-0 capitalize"
              >
                {condition.status}
              </Badge>
            </li>
          ))}
        </ul>
      )}
    </SectionCard>
  );
}
