import type { Metadata } from "next";

import { DocumentDetailContent } from "@/features/documents/components/document-detail-content";

export const metadata: Metadata = { title: "Document Details" };

export default async function DocumentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <DocumentDetailContent documentId={id} />;
}
