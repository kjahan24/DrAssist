import type { Metadata } from "next";

import { PrescriptionEditContent } from "@/features/prescriptions/components/prescription-edit-content";

export const metadata: Metadata = { title: "Edit Prescription" };

export default async function EditPrescriptionPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <PrescriptionEditContent prescriptionId={id} />;
}
