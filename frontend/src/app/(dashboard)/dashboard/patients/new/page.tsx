import type { Metadata } from "next";

import { PatientCreateContent } from "@/features/patients/components/patient-create-content";

export const metadata: Metadata = { title: "New Patient" };

export default function NewPatientPage() {
  return <PatientCreateContent />;
}
