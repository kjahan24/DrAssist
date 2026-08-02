import type { Metadata } from "next";

import { SoapNoteCreateContent } from "@/features/soap-notes/components/soap-note-create-content";

export const metadata: Metadata = { title: "New SOAP Note" };

export default function NewSoapNotePage() {
  return <SoapNoteCreateContent />;
}
