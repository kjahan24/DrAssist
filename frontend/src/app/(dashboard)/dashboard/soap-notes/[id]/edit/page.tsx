import type { Metadata } from "next";

import { SoapNoteEditContent } from "@/features/soap-notes/components/soap-note-edit-content";

export const metadata: Metadata = { title: "Edit SOAP Note" };

export default async function EditSoapNotePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <SoapNoteEditContent soapNoteId={id} />;
}
