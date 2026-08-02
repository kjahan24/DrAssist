import { Stethoscope } from "lucide-react";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/format";
import type { DiagnosisStatus, DiagnosisType, VisitDetail } from "@/lib/mock/visits";

const TYPE_LABEL: Record<DiagnosisType, string> = {
  primary: "Primary",
  secondary: "Secondary",
  differential: "Differential",
};

const STATUS_LABEL: Record<DiagnosisStatus, string> = {
  provisional: "Provisional",
  confirmed: "Confirmed",
  ruled_out: "Ruled Out",
};

export function DiagnosisSection({ visit }: { visit: VisitDetail }) {
  return (
    <SectionCard title="Diagnosis">
      {visit.diagnoses.length === 0 ? (
        <EmptyState icon={Stethoscope} title="No diagnoses recorded" />
      ) : (
        <ul className="divide-y">
          {visit.diagnoses.map((diagnosis) => (
            <li key={diagnosis.diagnosis_id} className="space-y-1 py-3 first:pt-0 last:pb-0">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-sm font-medium">{diagnosis.diagnosis_name}</p>
                {diagnosis.icd10_code && (
                  <span className="text-xs text-muted-foreground">({diagnosis.icd10_code})</span>
                )}
                <Badge variant="outline">{TYPE_LABEL[diagnosis.diagnosis_type]}</Badge>
                <Badge variant="secondary">{STATUS_LABEL[diagnosis.diagnosis_status]}</Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                Diagnosed {formatDate(diagnosis.diagnosed_at)}
              </p>
              {diagnosis.clinical_notes && <p className="text-sm">{diagnosis.clinical_notes}</p>}
            </li>
          ))}
        </ul>
      )}
    </SectionCard>
  );
}
