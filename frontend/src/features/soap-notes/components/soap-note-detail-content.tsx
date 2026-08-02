"use client";

import { AlertTriangle, Pencil } from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/dashboard/page-header";
import { PageSkeleton } from "@/components/dashboard/page-skeleton";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Button } from "@/components/ui/button";
import { AssessmentSection } from "@/features/soap-notes/components/detail/assessment-section";
import { AuditInformationSection } from "@/features/soap-notes/components/detail/audit-information-section";
import { ClinicalNoteReferenceSection } from "@/features/soap-notes/components/detail/clinical-note-reference-section";
import { DiagnosisSummarySection } from "@/features/soap-notes/components/detail/diagnosis-summary-section";
import { DoctorSummarySection } from "@/features/soap-notes/components/detail/doctor-summary-section";
import { ObjectiveSection } from "@/features/soap-notes/components/detail/objective-section";
import { PatientSummarySection } from "@/features/soap-notes/components/detail/patient-summary-section";
import { PlanSection } from "@/features/soap-notes/components/detail/plan-section";
import { PrescriptionSummarySection } from "@/features/soap-notes/components/detail/prescription-summary-section";
import { SubjectiveSection } from "@/features/soap-notes/components/detail/subjective-section";
import { VisitSummarySection } from "@/features/soap-notes/components/detail/visit-summary-section";
import { SoapNoteStatusBadge } from "@/features/soap-notes/components/soap-note-status-badge";
import { useSoapNote } from "@/features/soap-notes/hooks/use-soap-notes";
import { formatDate } from "@/lib/format";
import { isSoapNoteEditable } from "@/lib/mock/soap-notes";

export function SoapNoteDetailContent({ soapNoteId }: { soapNoteId: string }) {
  const { data: note, isLoading } = useSoapNote(soapNoteId);

  if (isLoading) {
    return <PageSkeleton title="SOAP Note" />;
  }

  if (!note) {
    return (
      <EmptyState
        titleAs="h1"
        icon={AlertTriangle}
        title="SOAP note not found"
        description="This note may have been removed, or the link is incorrect."
      />
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={note.soap_number}
        description={`${note.patient_name} · ${formatDate(note.created_at)}`}
        actions={
          <div className="flex items-center gap-2">
            <SoapNoteStatusBadge status={note.status} />
            {isSoapNoteEditable(note.status) && (
              <Button asChild>
                <Link href={`/dashboard/soap-notes/${note.soap_note_id}/edit`}>
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

      <div className="grid gap-6 sm:grid-cols-2">
        <SubjectiveSection note={note} />
        <ObjectiveSection note={note} />
        <AssessmentSection note={note} />
        <PlanSection note={note} />
      </div>

      <ClinicalNoteReferenceSection note={note} />
      <DiagnosisSummarySection note={note} />
      <PrescriptionSummarySection note={note} />
      <AuditInformationSection note={note} />
    </div>
  );
}
