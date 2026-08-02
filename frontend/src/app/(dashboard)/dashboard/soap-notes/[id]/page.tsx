import type { Metadata } from "next";

import { SoapNoteDetailContent } from "@/features/soap-notes/components/soap-note-detail-content";

export const metadata: Metadata = { title: "SOAP Note Details" };

export default async function SoapNoteDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <SoapNoteDetailContent soapNoteId={id} />;
}
