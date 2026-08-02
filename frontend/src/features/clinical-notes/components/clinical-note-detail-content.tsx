"use client";

import { AlertTriangle, Pencil } from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/dashboard/page-header";
import { PageSkeleton } from "@/components/dashboard/page-skeleton";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Button } from "@/components/ui/button";
import { ClinicalNoteStatusBadge } from "@/features/clinical-notes/components/clinical-note-status-badge";
import { AssessmentSection } from "@/features/clinical-notes/components/detail/assessment-section";
import { AttachmentsSection } from "@/features/clinical-notes/components/detail/attachments-section";
import { AuditInformationSection } from "@/features/clinical-notes/components/detail/audit-information-section";
import { ClinicalNarrativeSection } from "@/features/clinical-notes/components/detail/clinical-narrative-section";
import { DiagnosisSection } from "@/features/clinical-notes/components/detail/diagnosis-section";
import { DoctorSummarySection } from "@/features/clinical-notes/components/detail/doctor-summary-section";
import { PatientSummarySection } from "@/features/clinical-notes/components/detail/patient-summary-section";
import { PlanSection } from "@/features/clinical-notes/components/detail/plan-section";
import { PrescriptionSection } from "@/features/clinical-notes/components/detail/prescription-section";
import { SOAPNoteSection } from "@/features/clinical-notes/components/detail/soap-note-section";
import { VisitSummarySection } from "@/features/clinical-notes/components/detail/visit-summary-section";
import { useClinicalNote } from "@/features/clinical-notes/hooks/use-clinical-notes";
import { formatDate } from "@/lib/format";
import { getClinicalNoteTypeLabel, isClinicalNoteEditable } from "@/lib/mock/clinical-notes";

export function ClinicalNoteDetailContent({ clinicalNoteId }: { clinicalNoteId: string }) {
  const { data: note, isLoading } = useClinicalNote(clinicalNoteId);

  if (isLoading) {
    return <PageSkeleton title="Clinical Note" />;
  }

  if (!note) {
    return (
      <EmptyState
        titleAs="h1"
        icon={AlertTriangle}
        title="Clinical note not found"
        description="This note may have been removed, or the link is incorrect."
      />
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={note.note_number}
        description={`${note.patient_name} · ${getClinicalNoteTypeLabel(note.note_type)} · ${formatDate(
          note.encounter_datetime,
        )}`}
        actions={
          <div className="flex items-center gap-2">
            <ClinicalNoteStatusBadge status={note.status} />
            {isClinicalNoteEditable(note.status) && (
              <Button asChild>
                <Link href={`/dashboard/clinical-notes/${note.clinical_note_id}/edit`}>
                  <Pencil className="size-4" />
                  Edit Note
                </Link>
              </Button>
            )}
          </div>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <PatientSummarySection note={note} />
        <DoctorSummarySection note={note} />
        <VisitSummarySection note={note} />
      </div>

      <ClinicalNarrativeSection note={note} />
      <AssessmentSection note={note} />
      <PlanSection note={note} />
      <AttachmentsSection note={note} />
      <SOAPNoteSection note={note} />
      <DiagnosisSection note={note} />
      <PrescriptionSection note={note} />
      <AuditInformationSection note={note} />
    </div>
  );
}
