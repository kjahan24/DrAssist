import type { Metadata } from "next";

import { VisitDetailContent } from "@/features/visits/components/visit-detail-content";

export const metadata: Metadata = { title: "Visit Details" };

export default async function VisitDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <VisitDetailContent visitId={id} />;
}
