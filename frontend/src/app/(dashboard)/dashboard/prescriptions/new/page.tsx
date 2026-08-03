import type { Metadata } from "next";

import { PrescriptionCreateContent } from "@/features/prescriptions/components/prescription-create-content";

export const metadata: Metadata = { title: "New Prescription" };

export default function NewPrescriptionPage() {
  return <PrescriptionCreateContent />;
}
