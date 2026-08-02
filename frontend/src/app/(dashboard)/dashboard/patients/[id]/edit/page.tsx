import type { Metadata } from "next";

import { PatientEditContent } from "@/features/patients/components/patient-edit-content";

export const metadata: Metadata = { title: "Edit Patient" };

export default async function EditPatientPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <PatientEditContent patientId={id} />;
}
