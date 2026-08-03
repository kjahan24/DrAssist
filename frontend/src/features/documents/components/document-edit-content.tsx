"use client";

import { AlertTriangle, Lock } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { PageHeader } from "@/components/dashboard/page-header";
import { PageSkeleton } from "@/components/dashboard/page-skeleton";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Button } from "@/components/ui/button";
import { DocumentUploader } from "@/features/documents/components/document-uploader";
import { useDocument, useUpdateDocument } from "@/features/documents/hooks/use-documents";
import {
  documentToFormInput,
  getDocumentStatusLabel,
  isDocumentEditable,
  type DocumentUpdateInput,
} from "@/lib/mock/documents";

export function DocumentEditContent({ documentId }: { documentId: string }) {
  const router = useRouter();
  const { data: document, isLoading } = useDocument(documentId);
  const updateDocument = useUpdateDocument(documentId);

  if (isLoading) {
    return <PageSkeleton title="Edit Document" />;
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

  // Archived/deleted documents are treated as read-only — see
  // `isDocumentEditable()`'s docstring in `lib/mock/documents.ts`.
  if (!isDocumentEditable(document.status)) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Edit Document"
          description={`${document.document_number} is no longer editable.`}
        />
        <EmptyState
          icon={Lock}
          title={`This document is ${getDocumentStatusLabel(document.status).toLowerCase()}`}
          description="Archived and deleted documents cannot be edited."
          action={
            <Button variant="outline" asChild>
              <Link href={`/dashboard/documents/${documentId}`}>View Document</Link>
            </Button>
          }
        />
      </div>
    );
  }

  function handleSubmit(values: DocumentUpdateInput) {
    updateDocument.mutate(values, {
      onSuccess: () => {
        router.push(`/dashboard/documents/${documentId}`);
      },
    });
  }

  return (
    <div className="max-w-4xl space-y-6">
      <PageHeader
        title="Edit Document"
        description={`Update ${document.document_number} for ${document.patient_name}.`}
      />
      <DocumentUploader
        mode="edit"
        document={document}
        defaultValues={documentToFormInput(document)}
        onSubmit={handleSubmit}
        isSubmitting={updateDocument.isPending}
      />
    </div>
  );
}
