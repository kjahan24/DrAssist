import type { Metadata } from "next";

import { ClinicalNoteCreateContent } from "@/features/clinical-notes/components/clinical-note-create-content";

export const metadata: Metadata = { title: "New Clinical Note" };

export default function NewClinicalNotePage() {
  return <ClinicalNoteCreateContent />;
}
