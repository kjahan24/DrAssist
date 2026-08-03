import type { Metadata } from "next";

import { DocumentListContent } from "@/features/documents/components/document-list-content";

export const metadata: Metadata = { title: "Documents" };

export default function DocumentsPage() {
  return <DocumentListContent />;
}
