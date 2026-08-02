"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { LoadingButton } from "@/components/auth/loading-button";
import { FormInput } from "@/components/shared/forms/form-input";
import { FormSelect } from "@/components/shared/forms/form-select";
import { FormTextarea } from "@/components/shared/forms/form-textarea";
import { Form } from "@/components/ui/form";
import { AppointmentFormSection } from "@/features/appointments/components/appointment-form-section";
import { DoctorCombobox } from "@/features/appointments/components/doctor-combobox";
import { PatientCombobox } from "@/features/appointments/components/patient-combobox";
import { formatTime } from "@/lib/format";
import {
  APPOINTMENT_TYPE_OPTIONS,
  DEFAULT_SLOT_DURATION_MINUTES,
  TIME_SLOTS,
  computeEndTime,
  type AppointmentFormInput,
} from "@/lib/mock/appointments";

const TIME_SLOT_OPTIONS = TIME_SLOTS.map((slot) => ({ label: formatTime(slot), value: slot }));

const appointmentFormSchema = z.object({
  patient_id: z.string().min(1, "Select a patient"),
  doctor_id: z.string().min(1, "Select a doctor"),
  appointment_date: z.string().min(1, "Date is required"),
  start_time: z.string().min(1, "Select a time slot"),
  end_time: z.string().min(1, "Select a time slot"),
  appointment_type: z.enum(["consultation", "follow_up", "emergency", "telemedicine", "procedure"]),
  reason_for_visit: z.string(),
  notes: z.string(),
}) satisfies z.ZodType<AppointmentFormInput>;

const EMPTY_DEFAULTS: AppointmentFormInput = {
  patient_id: "",
  doctor_id: "",
  appointment_date: "",
  start_time: "",
  end_time: "",
  appointment_type: "consultation",
  reason_for_visit: "",
  notes: "",
};

interface AppointmentFormProps {
  defaultValues?: AppointmentFormInput;
  onSubmit: (values: AppointmentFormInput) => void;
  isSubmitting?: boolean;
  submitLabel?: string;
}

// Shared by both the New Appointment and Edit Appointment pages (per
// this module's "Edit Appointment: Reuse the same form" requirement).
// `end_time` has no field of its own in the UI — booking is slot-based
// (fixed `DEFAULT_SLOT_DURATION_MINUTES` increments, see
// `lib/mock/appointments.ts`), so it's derived from `start_time`
// whenever the selected slot changes, keeping "Time slot selector" a
// single control instead of two independent start/end pickers a user
// could set inconsistently.
export function AppointmentForm({
  defaultValues,
  onSubmit,
  isSubmitting,
  submitLabel = "Save Appointment",
}: AppointmentFormProps) {
  const form = useForm<AppointmentFormInput>({
    resolver: zodResolver(appointmentFormSchema),
    defaultValues: defaultValues ?? EMPTY_DEFAULTS,
  });

  const startTime = form.watch("start_time");
  const endTime = form.watch("end_time");

  useEffect(() => {
    if (startTime) {
      form.setValue("end_time", computeEndTime(startTime, DEFAULT_SLOT_DURATION_MINUTES), {
        shouldValidate: true,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [startTime]);

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6" noValidate>
        <AppointmentFormSection title="Appointment Details">
          <PatientCombobox control={form.control} name="patient_id" />
          <DoctorCombobox control={form.control} name="doctor_id" />
          <FormInput control={form.control} name="appointment_date" label="Date" type="date" />
          <FormSelect
            control={form.control}
            name="start_time"
            label="Time Slot"
            options={TIME_SLOT_OPTIONS}
            placeholder="Select a time"
            description={endTime ? `Ends at ${formatTime(endTime)}` : undefined}
          />
          <FormSelect
            control={form.control}
            name="appointment_type"
            label="Visit Type"
            options={APPOINTMENT_TYPE_OPTIONS}
          />
        </AppointmentFormSection>

        <AppointmentFormSection title="Additional Information">
          <div className="sm:col-span-2">
            <FormTextarea
              control={form.control}
              name="reason_for_visit"
              label="Reason for Visit"
              rows={2}
            />
          </div>
          <div className="sm:col-span-2">
            <FormTextarea control={form.control} name="notes" label="Notes" rows={4} />
          </div>
        </AppointmentFormSection>

        <div className="flex justify-end gap-3">
          <LoadingButton type="submit" loading={isSubmitting}>
            {submitLabel}
          </LoadingButton>
        </div>
      </form>
    </Form>
  );
}
