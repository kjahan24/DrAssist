"use client";

import { PageHeader } from "@/components/dashboard/page-header";
import { DocumentUploader } from "@/features/documents/components/document-uploader";

export function DocumentUploadContent() {
  return (
    <div className="max-w-4xl space-y-6">
      <PageHeader
        title="Upload Document"
        description="Add one or more documents to a patient's health record."
      />
      <DocumentUploader mode="upload" />
    </div>
  );
}
