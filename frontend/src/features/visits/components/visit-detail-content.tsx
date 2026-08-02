"use client";

import { AlertTriangle, Pencil } from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/dashboard/page-header";
import { PageSkeleton } from "@/components/dashboard/page-skeleton";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Button } from "@/components/ui/button";
import { ChiefComplaintSection } from "@/features/visits/components/detail/chief-complaint-section";
import { DiagnosisSection } from "@/features/visits/components/detail/diagnosis-section";
import { DocumentsSection } from "@/features/visits/components/detail/documents-section";
import { PrescriptionsSection } from "@/features/visits/components/detail/prescriptions-section";
import { SOAPSummarySection } from "@/features/visits/components/detail/soap-summary-section";
import { VisitInfoSection } from "@/features/visits/components/detail/visit-info-section";
import { VitalSignsSection } from "@/features/visits/components/detail/vital-signs-section";
import { VisitStatusBadge } from "@/features/visits/components/visit-status-badge";
import { VisitSummary } from "@/features/visits/components/visit-summary";
import { VisitTimeline } from "@/features/visits/components/visit-timeline";
import { useVisit } from "@/features/visits/hooks/use-visits";
import { formatDate } from "@/lib/format";
import { getDoctorInitials } from "@/lib/mock/doctors";
import { getPatientInitials } from "@/lib/mock/visits";

export function VisitDetailContent({ visitId }: { visitId: string }) {
  const { data: visit, isLoading } = useVisit(visitId);

  if (isLoading) {
    return <PageSkeleton title="Visit Details" />;
  }

  if (!visit) {
    return (
      <EmptyState
        titleAs="h1"
        icon={AlertTriangle}
        title="Visit not found"
        description="This visit may have been removed, or the link is incorrect."
      />
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={visit.visit_number}
        description={`${visit.patient_name} with ${visit.doctor_name} · ${formatDate(visit.visit_date)}`}
        actions={
          <div className="flex items-center gap-2">
            <VisitStatusBadge status={visit.visit_status} />
            <Button asChild>
              <Link href={`/dashboard/visits/${visit.visit_id}/edit`}>
                <Pencil className="size-4" />
                Edit Visit
              </Link>
            </Button>
          </div>
        }
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <VisitInfoSection visit={visit} />
        <VisitSummary
          title="Patient Summary"
          name={visit.patient_name}
          initials={getPatientInitials(visit)}
          fields={[{ label: "Patient ID", value: visit.patient_number }]}
          href={`/dashboard/patients/${visit.patient_id}`}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <VisitSummary
          title="Doctor Summary"
          name={visit.doctor_name}
          initials={getDoctorInitials({ full_name: visit.doctor_name })}
          fields={[{ label: "Department", value: visit.department }]}
        />
        <ChiefComplaintSection visit={visit} />
      </div>

      <VitalSignsSection visit={visit} />
      <SOAPSummarySection visit={visit} />
      <DiagnosisSection visit={visit} />
      <PrescriptionsSection visit={visit} />
      <DocumentsSection visit={visit} />
      <VisitTimeline events={visit.timeline_events} />
    </div>
  );
}
