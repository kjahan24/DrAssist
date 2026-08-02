import { FileText } from "lucide-react";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import { ClinicalNotePreview } from "@/features/clinical-notes/components/clinical-note-preview";
import type { ClinicalNoteDetail } from "@/lib/mock/clinical-notes";

export function SOAPNoteSection({ note }: { note: ClinicalNoteDetail }) {
  const soap = note.soap_note;

  return (
    <SectionCard
      title="Related SOAP Note"
      description="Subjective, Objective, Assessment, and Plan."
    >
      {!soap ? (
        <EmptyState icon={FileText} title="No SOAP note recorded" />
      ) : (
        <ClinicalNotePreview
          fields={[
            { label: "Chief Complaint", value: soap.chief_complaint },
            { label: "History of Present Illness", value: soap.history_of_present_illness },
            { label: "Review of Systems", value: soap.review_of_systems },
            { label: "Physical Examination", value: soap.physical_examination },
            { label: "Assessment", value: soap.assessment },
            { label: "Plan", value: soap.plan },
          ]}
        />
      )}
    </SectionCard>
  );
}
