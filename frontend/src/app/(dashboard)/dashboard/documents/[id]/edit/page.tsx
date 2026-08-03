import type { Metadata } from "next";

import { DocumentEditContent } from "@/features/documents/components/document-edit-content";

export const metadata: Metadata = { title: "Edit Document" };

export default async function DocumentEditPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <DocumentEditContent documentId={id} />;
}
