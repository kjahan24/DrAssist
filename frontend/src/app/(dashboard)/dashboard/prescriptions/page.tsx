import type { Metadata } from "next";

import { PrescriptionListContent } from "@/features/prescriptions/components/prescription-list-content";

export const metadata: Metadata = { title: "Prescriptions" };

export default function PrescriptionsPage() {
  return <PrescriptionListContent />;
}
