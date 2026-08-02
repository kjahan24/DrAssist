import type { Metadata } from "next";

import { VisitEditContent } from "@/features/visits/components/visit-edit-content";

export const metadata: Metadata = { title: "Edit Visit" };

export default async function EditVisitPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <VisitEditContent visitId={id} />;
}
