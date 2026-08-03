"use client";

import { AlertTriangle, Download, Pencil } from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/dashboard/page-header";
import { PageSkeleton } from "@/components/dashboard/page-skeleton";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Button } from "@/components/ui/button";
import { AuditInformationSection } from "@/features/documents/components/detail/audit-information-section";
import { DocumentInformationSection } from "@/features/documents/components/detail/document-information-section";
import { PatientSummarySection } from "@/features/documents/components/detail/patient-summary-section";
import { RelatedClinicalNoteSection } from "@/features/documents/components/detail/related-clinical-note-section";
import { RelatedLabReportSection } from "@/features/documents/components/detail/related-lab-report-section";
import { RelatedPrescriptionSection } from "@/features/documents/components/detail/related-prescription-section";
import { RelatedVisitSection } from "@/features/documents/components/detail/related-visit-section";
import { TagsSection } from "@/features/documents/components/detail/tags-section";
import { VersionHistorySection } from "@/features/documents/components/detail/version-history-section";
import { DocumentStatusBadge } from "@/features/documents/components/document-status-badge";
import { DocumentViewer } from "@/features/documents/components/document-viewer";
import { useDocument } from "@/features/documents/hooks/use-documents";
import { showSimulatedDownloadToast } from "@/features/documents/lib/simulated-download";
import { isDocumentEditable } from "@/lib/mock/documents";

export function DocumentDetailContent({ documentId }: { documentId: string }) {
  const { data: document, isLoading } = useDocument(documentId);

  if (isLoading) {
    return <PageSkeleton title="Document" />;
  }

  if (!document) {
    return (
      <EmptyState
        titleAs="h1"
        icon={AlertTriangle}
        title="Document not found"
        description="This document may have been removed, or the link is incorrect."
      />
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={document.title}
        description={`${document.document_number} · ${document.patient_name}`}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <DocumentStatusBadge status={document.status} />
            <Button variant="outline" onClick={() => showSimulatedDownloadToast(document)}>
              <Download className="size-4" />
              Download
            </Button>
            {isDocumentEditable(document.status) && (
              <Button asChild>
                <Link href={`/dashboard/documents/${document.document_id}/edit`}>
                  <Pencil className="size-4" />
                  Edit Document
                </Link>
              </Button>
            )}
          </div>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <PatientSummarySection document={document} />
        <div className="lg:col-span-2">
          <DocumentInformationSection document={document} />
        </div>
      </div>

      <TagsSection document={document} />
      <DocumentViewer document={document} />
      <VersionHistorySection document={document} />

      <div className="grid gap-6 lg:grid-cols-2">
        <RelatedVisitSection document={document} />
        <RelatedClinicalNoteSection document={document} />
        <RelatedLabReportSection document={document} />
        <RelatedPrescriptionSection document={document} />
      </div>

      <AuditInformationSection document={document} />
    </div>
  );
}
