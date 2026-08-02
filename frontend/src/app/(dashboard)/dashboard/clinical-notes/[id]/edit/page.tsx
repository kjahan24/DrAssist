import type { Metadata } from "next";

import { ClinicalNoteEditContent } from "@/features/clinical-notes/components/clinical-note-edit-content";

export const metadata: Metadata = { title: "Edit Clinical Note" };

export default async function EditClinicalNotePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ClinicalNoteEditContent clinicalNoteId={id} />;
}
