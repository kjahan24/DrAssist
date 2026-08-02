"use client";

import { useRouter } from "next/navigation";

import { PageHeader } from "@/components/dashboard/page-header";
import { PatientForm } from "@/features/patients/components/patient-form";
import { useCreatePatient } from "@/features/patients/hooks/use-patients";
import type { PatientFormInput } from "@/lib/mock/patients";

export function PatientCreateContent() {
  const router = useRouter();
  const createPatient = useCreatePatient();

  function handleSubmit(values: PatientFormInput) {
    createPatient.mutate(values, {
      onSuccess: (patient) => {
        router.push(`/dashboard/patients/${patient.patient_id}`);
      },
    });
  }

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader title="Add Patient" description="Register a new patient record." />
      <PatientForm
        onSubmit={handleSubmit}
        isSubmitting={createPatient.isPending}
        submitLabel="Create Patient"
      />
    </div>
  );
}
