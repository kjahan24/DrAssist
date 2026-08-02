import type { Metadata } from "next";

import { SoapNoteListContent } from "@/features/soap-notes/components/soap-note-list-content";

export const metadata: Metadata = { title: "SOAP Notes" };

export default function SoapNotesPage() {
  return <SoapNoteListContent />;
}
