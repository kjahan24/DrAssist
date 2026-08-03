import type { Metadata } from "next";

import { DocumentUploadContent } from "@/features/documents/components/document-upload-content";

export const metadata: Metadata = { title: "Upload Document" };

export default function DocumentUploadPage() {
  return <DocumentUploadContent />;
}
