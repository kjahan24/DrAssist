"use client";

import { useRouter } from "next/navigation";

import { PageHeader } from "@/components/dashboard/page-header";
import { AppointmentForm } from "@/features/appointments/components/appointment-form";
import { useCreateAppointment } from "@/features/appointments/hooks/use-appointments";
import type { AppointmentFormInput } from "@/lib/mock/appointments";

export function AppointmentCreateContent() {
  const router = useRouter();
  const createAppointment = useCreateAppointment();

  function handleSubmit(values: AppointmentFormInput) {
    createAppointment.mutate(values, {
      onSuccess: (appointment) => {
        router.push(`/dashboard/appointments/${appointment.appointment_id}`);
      },
    });
  }

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader title="New Appointment" description="Schedule a new patient appointment." />
      <AppointmentForm
        onSubmit={handleSubmit}
        isSubmitting={createAppointment.isPending}
        submitLabel="Create Appointment"
      />
    </div>
  );
}
