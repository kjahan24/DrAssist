"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { LoadingButton } from "@/components/auth/loading-button";
import { FormInput } from "@/components/shared/forms/form-input";
import { FormSelect } from "@/components/shared/forms/form-select";
import { FormTextarea } from "@/components/shared/forms/form-textarea";
import { Form } from "@/components/ui/form";
import { DoctorCombobox } from "@/features/appointments/components/doctor-combobox";
import { PatientCombobox } from "@/features/appointments/components/patient-combobox";
import { AppointmentCombobox } from "@/features/visits/components/appointment-combobox";
import { VisitFormSection } from "@/features/visits/components/visit-form-section";
import { VISIT_TYPE_OPTIONS, type VisitFormInput } from "@/lib/mock/visits";

const visitFormSchema = z.object({
  patient_id: z.string().min(1, "Select a patient"),
  doctor_id: z.string().min(1, "Select a doctor"),
  appointment_id: z.string(),
  visit_date: z.string().min(1, "Visit date is required"),
  visit_type: z.enum([
    "consultation",
    "follow_up",
    "emergency",
    "telemedicine",
    "procedure",
    "lab_review",
    "vaccination",
    "home_visit",
  ]),
  chief_complaint_summary: z.string(),
  notes: z.string(),
}) satisfies z.ZodType<VisitFormInput>;

const EMPTY_DEFAULTS: VisitFormInput = {
  patient_id: "",
  doctor_id: "",
  appointment_id: "",
  visit_date: "",
  visit_type: "consultation",
  chief_complaint_summary: "",
  notes: "",
};

interface VisitFormProps {
  defaultValues?: VisitFormInput;
  onSubmit: (values: VisitFormInput) => void;
  isSubmitting?: boolean;
  submitLabel?: string;
}

// Shared by both the New Visit and Edit Visit pages (per this module's
// "Edit Visit: Reuse the same form" requirement). `PatientCombobox`/
// `DoctorCombobox` are reused directly from
// `features/appointments/components/` rather than duplicated — both are
// generic `{control, name, label}` selectors with no appointment-specific
// business logic, so importing the already-built ones is more direct
// than re-implementing near-identical code (unlike `VisitFormSection`,
// which stays its own file since it's pure, trivial markup, not
// meaningfully shared logic).
export function VisitForm({
  defaultValues,
  onSubmit,
  isSubmitting,
  submitLabel = "Save Visit",
}: VisitFormProps) {
  const form = useForm<VisitFormInput>({
    resolver: zodResolver(visitFormSchema),
    defaultValues: defaultValues ?? EMPTY_DEFAULTS,
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6" noValidate>
        <VisitFormSection title="Visit Details">
          <PatientCombobox control={form.control} name="patient_id" />
          <DoctorCombobox control={form.control} name="doctor_id" />
          <AppointmentCombobox control={form.control} name="appointment_id" />
          <FormInput control={form.control} name="visit_date" label="Visit Date" type="date" />
          <FormSelect
            control={form.control}
            name="visit_type"
            label="Visit Type"
            options={VISIT_TYPE_OPTIONS}
          />
        </VisitFormSection>

        <VisitFormSection title="Additional Information">
          <div className="sm:col-span-2">
            <FormTextarea
              control={form.control}
              name="chief_complaint_summary"
              label="Chief Complaint"
              rows={2}
            />
          </div>
          <div className="sm:col-span-2">
            <FormTextarea control={form.control} name="notes" label="Notes" rows={4} />
          </div>
        </VisitFormSection>

        <div className="flex justify-end gap-3">
          <LoadingButton type="submit" loading={isSubmitting}>
            {submitLabel}
          </LoadingButton>
        </div>
      </form>
    </Form>
  );
}
