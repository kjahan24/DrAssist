"use client";

import { AlertTriangle, Pencil } from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/dashboard/page-header";
import { PageSkeleton } from "@/components/dashboard/page-skeleton";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Button } from "@/components/ui/button";
import { AuditInformationSection } from "@/features/prescriptions/components/detail/audit-information-section";
import { ClinicalNoteReferenceSection } from "@/features/prescriptions/components/detail/clinical-note-reference-section";
import { DiagnosisSection } from "@/features/prescriptions/components/detail/diagnosis-section";
import { DoctorSummarySection } from "@/features/prescriptions/components/detail/doctor-summary-section";
import { MedicationListSection } from "@/features/prescriptions/components/detail/medication-list-section";
import { NotesSection } from "@/features/prescriptions/components/detail/notes-section";
import { PatientSummarySection } from "@/features/prescriptions/components/detail/patient-summary-section";
import { SoapNoteReferenceSection } from "@/features/prescriptions/components/detail/soap-note-reference-section";
import { VisitSummarySection } from "@/features/prescriptions/components/detail/visit-summary-section";
import { PrescriptionStatusBadge } from "@/features/prescriptions/components/prescription-status-badge";
import { usePrescription } from "@/features/prescriptions/hooks/use-prescriptions";
import { formatDate } from "@/lib/format";
import { isPrescriptionEditable } from "@/lib/mock/prescriptions";

export function PrescriptionDetailContent({ prescriptionId }: { prescriptionId: string }) {
  const { data: prescription, isLoading } = usePrescription(prescriptionId);

  if (isLoading) {
    return <PageSkeleton title="Prescription" />;
  }

  if (!prescription) {
    return (
      <EmptyState
        titleAs="h1"
        icon={AlertTriangle}
        title="Prescription not found"
        description="This prescription may have been removed, or the link is incorrect."
      />
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={prescription.prescription_number}
        description={`${prescription.patient_name} · ${formatDate(prescription.prescription_date)}`}
        actions={
          <div className="flex items-center gap-2">
            <PrescriptionStatusBadge status={prescription.status} />
            {isPrescriptionEditable(prescription.status) && (
              <Button asChild>
                <Link href={`/dashboard/prescriptions/${prescription.prescription_id}/edit`}>
                  <Pencil className="size-4" />
                  Edit Prescription
                </Link>
              </Button>
            )}
          </div>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <PatientSummarySection prescription={prescription} />
        <DoctorSummarySection prescription={prescription} />
        <VisitSummarySection prescription={prescription} />
      </div>

      <MedicationListSection prescription={prescription} />
      <NotesSection prescription={prescription} />

      <div className="grid gap-6 lg:grid-cols-2">
        <DiagnosisSection prescription={prescription} />
        <ClinicalNoteReferenceSection prescription={prescription} />
      </div>

      <SoapNoteReferenceSection prescription={prescription} />
      <AuditInformationSection prescription={prescription} />
    </div>
  );
}
