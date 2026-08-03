"use client";

import { useRouter } from "next/navigation";

import { PageHeader } from "@/components/dashboard/page-header";
import { PrescriptionForm } from "@/features/prescriptions/components/prescription-form";
import { useCreatePrescription } from "@/features/prescriptions/hooks/use-prescriptions";
import type { PrescriptionFormInput, PrescriptionStatus } from "@/lib/mock/prescriptions";

export function PrescriptionCreateContent() {
  const router = useRouter();
  const createPrescription = useCreatePrescription();

  function handleSubmit(values: PrescriptionFormInput, status: PrescriptionStatus) {
    createPrescription.mutate(
      { input: values, status },
      {
        onSuccess: (prescription) => {
          router.push(`/dashboard/prescriptions/${prescription.prescription_id}`);
        },
      },
    );
  }

  return (
    <div className="max-w-4xl space-y-6">
      <PageHeader title="New Prescription" description="Write a new patient prescription." />
      <PrescriptionForm onSubmit={handleSubmit} isSubmitting={createPrescription.isPending} />
    </div>
  );
}
