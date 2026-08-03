"use client";

import { AlertTriangle, Lock } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { PageHeader } from "@/components/dashboard/page-header";
import { PageSkeleton } from "@/components/dashboard/page-skeleton";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Button } from "@/components/ui/button";
import { PrescriptionForm } from "@/features/prescriptions/components/prescription-form";
import {
  usePrescription,
  useUpdatePrescription,
} from "@/features/prescriptions/hooks/use-prescriptions";
import {
  getPrescriptionStatusLabel,
  isPrescriptionEditable,
  prescriptionToFormInput,
  type PrescriptionFormInput,
  type PrescriptionStatus,
} from "@/lib/mock/prescriptions";

export function PrescriptionEditContent({ prescriptionId }: { prescriptionId: string }) {
  const router = useRouter();
  const { data: prescription, isLoading } = usePrescription(prescriptionId);
  const updatePrescription = useUpdatePrescription(prescriptionId);

  if (isLoading) {
    return <PageSkeleton title="Edit Prescription" />;
  }

  if (!prescription) {
    return (
      <EmptyState
        titleAs="h1"
        icon={AlertTriangle}
        title="Prescription not found"
        description="This prescription may have been removed, or the link is incorrect."
      />
    );
  }

  // A Final prescription is treated as immutable, mirroring the real,
  // strict Draft-only editability of `Prescription` — see
  // `lib/mock/prescriptions.ts`'s docstring.
  if (!isPrescriptionEditable(prescription.status)) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Edit Prescription"
          description={`${prescription.prescription_number} is no longer editable.`}
        />
        <EmptyState
          icon={Lock}
          title={`This prescription is ${getPrescriptionStatusLabel(prescription.status).toLowerCase()}`}
          description="Final prescriptions cannot be edited, matching the real clinical documentation workflow."
          action={
            <Button variant="outline" asChild>
              <Link href={`/dashboard/prescriptions/${prescriptionId}`}>View Prescription</Link>
            </Button>
          }
        />
      </div>
    );
  }

  function handleSubmit(values: PrescriptionFormInput, status: PrescriptionStatus) {
    updatePrescription.mutate(
      { input: values, status },
      {
        onSuccess: () => {
          router.push(`/dashboard/prescriptions/${prescriptionId}`);
        },
      },
    );
  }

  return (
    <div className="max-w-4xl space-y-6">
      <PageHeader
        title="Edit Prescription"
        description={`Update ${prescription.prescription_number} for ${prescription.patient_name}.`}
      />
      <PrescriptionForm
        defaultValues={prescriptionToFormInput(prescription)}
        onSubmit={handleSubmit}
        isSubmitting={updatePrescription.isPending}
      />
    </div>
  );
}
