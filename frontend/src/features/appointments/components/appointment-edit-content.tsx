"use client";

import { AlertTriangle } from "lucide-react";
import { useRouter } from "next/navigation";

import { PageHeader } from "@/components/dashboard/page-header";
import { PageSkeleton } from "@/components/dashboard/page-skeleton";
import { EmptyState } from "@/components/shared/states/empty-state";
import { AppointmentForm } from "@/features/appointments/components/appointment-form";
import {
  useAppointment,
  useUpdateAppointment,
} from "@/features/appointments/hooks/use-appointments";
import { appointmentToFormInput, type AppointmentFormInput } from "@/lib/mock/appointments";

export function AppointmentEditContent({ appointmentId }: { appointmentId: string }) {
  const router = useRouter();
  const { data: appointment, isLoading } = useAppointment(appointmentId);
  const updateAppointment = useUpdateAppointment(appointmentId);

  if (isLoading) {
    return <PageSkeleton title="Edit Appointment" />;
  }

  if (!appointment) {
    return (
      <EmptyState
        titleAs="h1"
        icon={AlertTriangle}
        title="Appointment not found"
        description="This appointment may have been removed, or the link is incorrect."
      />
    );
  }

  function handleSubmit(values: AppointmentFormInput) {
    updateAppointment.mutate(values, {
      onSuccess: () => {
        router.push(`/dashboard/appointments/${appointmentId}`);
      },
    });
  }

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader
        title="Edit Appointment"
        description={`Update ${appointment.appointment_number} for ${appointment.patient_name}.`}
      />
      <AppointmentForm
        defaultValues={appointmentToFormInput(appointment)}
        onSubmit={handleSubmit}
        isSubmitting={updateAppointment.isPending}
        submitLabel="Save Changes"
      />
    </div>
  );
}
