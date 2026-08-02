"use client";

import { AlertTriangle, Pencil } from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/dashboard/page-header";
import { PageSkeleton } from "@/components/dashboard/page-skeleton";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Button } from "@/components/ui/button";
import { AttachmentsSection } from "@/features/lab-reports/components/detail/attachments-section";
import { AuditInformationSection } from "@/features/lab-reports/components/detail/audit-information-section";
import { ClinicalNoteReferenceSection } from "@/features/lab-reports/components/detail/clinical-note-reference-section";
import { DoctorSummarySection } from "@/features/lab-reports/components/detail/doctor-summary-section";
import { InterpretationSection } from "@/features/lab-reports/components/detail/interpretation-section";
import { PatientSummarySection } from "@/features/lab-reports/components/detail/patient-summary-section";
import { ReferenceRangesSection } from "@/features/lab-reports/components/detail/reference-ranges-section";
import { ReportInformationSection } from "@/features/lab-reports/components/detail/report-information-section";
import { SoapNoteReferenceSection } from "@/features/lab-reports/components/detail/soap-note-reference-section";
import { TestResultsSection } from "@/features/lab-reports/components/detail/test-results-section";
import { VisitSummarySection } from "@/features/lab-reports/components/detail/visit-summary-section";
import { LabReportStatusBadge } from "@/features/lab-reports/components/lab-report-status-badge";
import { useLabReport } from "@/features/lab-reports/hooks/use-lab-reports";
import { formatDate } from "@/lib/format";
import { isLabReportEditable } from "@/lib/mock/lab-reports";

export function LabReportDetailContent({ labReportId }: { labReportId: string }) {
  const { data: report, isLoading } = useLabReport(labReportId);

  if (isLoading) {
    return <PageSkeleton title="Lab Report" />;
  }

  if (!report) {
    return (
      <EmptyState
        titleAs="h1"
        icon={AlertTriangle}
        title="Lab report not found"
        description="This report may have been removed, or the link is incorrect."
      />
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={report.report_number}
        description={`${report.patient_name} · ${formatDate(report.ordered_at)}`}
        actions={
          <div className="flex items-center gap-2">
            <LabReportStatusBadge status={report.status} />
            {isLabReportEditable(report.status) && (
              <Button asChild>
                <Link href={`/dashboard/lab-reports/${report.lab_report_id}/edit`}>
                  <Pencil className="size-4" />
                  Edit Report
                </Link>
              </Button>
            )}
          </div>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <PatientSummarySection report={report} />
        <DoctorSummarySection report={report} />
        <VisitSummarySection report={report} />
      </div>

      <ReportInformationSection report={report} />
      <TestResultsSection report={report} />
      <ReferenceRangesSection report={report} />
      <InterpretationSection report={report} />
      <AttachmentsSection report={report} />

      <div className="grid gap-6 lg:grid-cols-2">
        <ClinicalNoteReferenceSection report={report} />
        <SoapNoteReferenceSection report={report} />
      </div>

      <AuditInformationSection report={report} />
    </div>
  );
}
