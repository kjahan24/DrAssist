import type { Metadata } from "next";

import { PrescriptionDetailContent } from "@/features/prescriptions/components/prescription-detail-content";

export const metadata: Metadata = { title: "Prescription Details" };

export default async function PrescriptionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <PrescriptionDetailContent prescriptionId={id} />;
}
