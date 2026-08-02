import type { Metadata } from "next";

import { ClinicalNoteDetailContent } from "@/features/clinical-notes/components/clinical-note-detail-content";

export const metadata: Metadata = { title: "Clinical Note Details" };

export default async function ClinicalNoteDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ClinicalNoteDetailContent clinicalNoteId={id} />;
}
