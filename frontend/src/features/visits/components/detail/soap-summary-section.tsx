import { FileText } from "lucide-react";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import type { SOAPNote, VisitDetail } from "@/lib/mock/visits";

// `chief_complaint` (also present on the real `SOAPNote` entity) is
// intentionally not repeated here — it's already its own dedicated
// section above (`ChiefComplaintSection`) on this page.
const SOAP_FIELDS: { key: keyof Omit<SOAPNote, "chief_complaint">; label: string }[] = [
  { key: "history_of_present_illness", label: "History of Present Illness" },
  { key: "review_of_systems", label: "Review of Systems" },
  { key: "physical_examination", label: "Physical Examination" },
  { key: "assessment", label: "Assessment" },
  { key: "plan", label: "Plan" },
];

export function SOAPSummarySection({ visit }: { visit: VisitDetail }) {
  const note = visit.soap_note;

  return (
    <SectionCard title="SOAP Summary" description="Subjective, Objective, Assessment, and Plan.">
      {!note ? (
        <EmptyState icon={FileText} title="No SOAP note recorded" />
      ) : (
        <div className="space-y-4">
          {SOAP_FIELDS.map(({ key, label }) => (
            <div key={key}>
              <p className="text-xs font-medium text-muted-foreground">{label}</p>
              <p className="mt-1 text-sm">
                {note[key] || <span className="text-muted-foreground">Not documented.</span>}
              </p>
            </div>
          ))}
        </div>
      )}
    </SectionCard>
  );
}
