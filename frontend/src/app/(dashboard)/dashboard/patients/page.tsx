import type { Metadata } from "next";

import { PatientListContent } from "@/features/patients/components/patient-list-content";

export const metadata: Metadata = { title: "Patients" };

export default function PatientsPage() {
  return <PatientListContent />;
}
