"use client";

import { AlertTriangle } from "lucide-react";
import { useRouter } from "next/navigation";

import { PageHeader } from "@/components/dashboard/page-header";
import { PageSkeleton } from "@/components/dashboard/page-skeleton";
import { EmptyState } from "@/components/shared/states/empty-state";
import { PatientForm } from "@/features/patients/components/patient-form";
import { usePatient, useUpdatePatient } from "@/features/patients/hooks/use-patients";
import { getFullName, patientToFormInput, type PatientFormInput } from "@/lib/mock/patients";

export function PatientEditContent({ patientId }: { patientId: string }) {
  const router = useRouter();
  const { data: patient, isLoading } = usePatient(patientId);
  const updatePatient = useUpdatePatient(patientId);

  if (isLoading) {
    return <PageSkeleton title="Edit Patient" />;
  }

  if (!patient) {
    return (
      <EmptyState
        titleAs="h1"
        icon={AlertTriangle}
        title="Patient not found"
        description="This patient may have been removed, or the link is incorrect."
      />
    );
  }

  function handleSubmit(values: PatientFormInput) {
    updatePatient.mutate(values, {
      onSuccess: () => {
        router.push(`/dashboard/patients/${patientId}`);
      },
    });
  }

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader title="Edit Patient" description={`Update ${getFullName(patient)}'s record.`} />
      <PatientForm
        defaultValues={patientToFormInput(patient)}
        onSubmit={handleSubmit}
        isSubmitting={updatePatient.isPending}
        submitLabel="Save Changes"
      />
    </div>
  );
}
