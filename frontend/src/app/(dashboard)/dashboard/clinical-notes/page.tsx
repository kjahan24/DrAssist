import type { Metadata } from "next";

import { ClinicalNoteListContent } from "@/features/clinical-notes/components/clinical-note-list-content";

export const metadata: Metadata = { title: "Clinical Notes" };

export default function ClinicalNotesPage() {
  return <ClinicalNoteListContent />;
}
