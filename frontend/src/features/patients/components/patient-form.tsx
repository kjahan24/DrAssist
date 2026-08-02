"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { LoadingButton } from "@/components/auth/loading-button";
import { FormInput } from "@/components/shared/forms/form-input";
import { FormSelect } from "@/components/shared/forms/form-select";
import { Form } from "@/components/ui/form";
import { PatientFormSection } from "@/features/patients/components/patient-form-section";
import { BLOOD_GROUP_OPTIONS, GENDER_OPTIONS, type PatientFormInput } from "@/lib/mock/patients";

const STATUS_OPTIONS = [
  { label: "Active", value: "active" },
  { label: "Inactive", value: "inactive" },
] as const;

const patientFormSchema = z.object({
  first_name: z.string().min(1, "First name is required"),
  last_name: z.string().min(1, "Last name is required"),
  gender: z.enum(["male", "female", "other"]),
  date_of_birth: z.string().min(1, "Date of birth is required"),
  blood_group: z.enum(["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "unknown"]),
  status: z.enum(["active", "inactive"]),
  phone: z.string().min(1, "Phone number is required"),
  email: z.union([z.literal(""), z.string().email("Enter a valid email address")]),
  address_line1: z.string().min(1, "Address is required"),
  address_line2: z.string(),
  city: z.string().min(1, "City is required"),
  state: z.string().min(1, "State is required"),
  postal_code: z.string().min(1, "Postal code is required"),
  emergency_contact_name: z.string(),
  emergency_contact_relationship: z.string(),
  emergency_contact_phone: z.string(),
  insurance_provider: z.string(),
  insurance_policy_number: z.string(),
}) satisfies z.ZodType<PatientFormInput>;

const EMPTY_DEFAULTS: PatientFormInput = {
  first_name: "",
  last_name: "",
  gender: "male",
  date_of_birth: "",
  blood_group: "unknown",
  status: "active",
  phone: "",
  email: "",
  address_line1: "",
  address_line2: "",
  city: "",
  state: "",
  postal_code: "",
  emergency_contact_name: "",
  emergency_contact_relationship: "",
  emergency_contact_phone: "",
  insurance_provider: "",
  insurance_policy_number: "",
};

interface PatientFormProps {
  defaultValues?: PatientFormInput;
  onSubmit: (values: PatientFormInput) => void;
  isSubmitting?: boolean;
  submitLabel?: string;
}

// Shared by both the New Patient and Edit Patient pages (per this
// module's "Edit Patient: Reuse the same form" requirement) — the caller
// owns loading existing data (via `patientToFormInput`) and persisting
// (`useCreatePatient`/`useUpdatePatient`), this component owns only the
// fields, validation, and layout. Scope intentionally matches the real
// `RegisterPatient` backend use case (identity + contact + emergency +
// insurance) — see `lib/mock/patients.ts`'s module docstring.
export function PatientForm({
  defaultValues,
  onSubmit,
  isSubmitting,
  submitLabel = "Save Patient",
}: PatientFormProps) {
  const form = useForm<PatientFormInput>({
    resolver: zodResolver(patientFormSchema),
    defaultValues: defaultValues ?? EMPTY_DEFAULTS,
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6" noValidate>
        <PatientFormSection title="Basic Information">
          <FormInput
            control={form.control}
            name="first_name"
            label="First Name"
            autoComplete="given-name"
          />
          <FormInput
            control={form.control}
            name="last_name"
            label="Last Name"
            autoComplete="family-name"
          />
          <FormSelect
            control={form.control}
            name="gender"
            label="Gender"
            options={GENDER_OPTIONS}
          />
          <FormInput
            control={form.control}
            name="date_of_birth"
            label="Date of Birth"
            type="date"
          />
          <FormSelect
            control={form.control}
            name="blood_group"
            label="Blood Group"
            options={BLOOD_GROUP_OPTIONS}
          />
          <FormSelect
            control={form.control}
            name="status"
            label="Status"
            options={[...STATUS_OPTIONS]}
          />
        </PatientFormSection>

        <PatientFormSection title="Contact Information">
          <FormInput
            control={form.control}
            name="phone"
            label="Phone"
            type="tel"
            autoComplete="tel"
          />
          <FormInput
            control={form.control}
            name="email"
            label="Email"
            type="email"
            autoComplete="email"
          />
          <div className="sm:col-span-2">
            <FormInput
              control={form.control}
              name="address_line1"
              label="Address Line 1"
              autoComplete="address-line1"
            />
          </div>
          <div className="sm:col-span-2">
            <FormInput
              control={form.control}
              name="address_line2"
              label="Address Line 2"
              autoComplete="address-line2"
            />
          </div>
          <FormInput
            control={form.control}
            name="city"
            label="City"
            autoComplete="address-level2"
          />
          <FormInput
            control={form.control}
            name="state"
            label="State"
            autoComplete="address-level1"
          />
          <FormInput
            control={form.control}
            name="postal_code"
            label="Postal Code"
            autoComplete="postal-code"
          />
        </PatientFormSection>

        <PatientFormSection title="Emergency Contact" description="Optional.">
          <FormInput control={form.control} name="emergency_contact_name" label="Name" />
          <FormInput
            control={form.control}
            name="emergency_contact_relationship"
            label="Relationship"
          />
          <FormInput
            control={form.control}
            name="emergency_contact_phone"
            label="Phone"
            type="tel"
          />
        </PatientFormSection>

        <PatientFormSection title="Insurance" description="Optional.">
          <FormInput control={form.control} name="insurance_provider" label="Provider Name" />
          <FormInput control={form.control} name="insurance_policy_number" label="Policy Number" />
        </PatientFormSection>

        <div className="flex justify-end gap-3">
          <LoadingButton type="submit" loading={isSubmitting}>
            {submitLabel}
          </LoadingButton>
        </div>
      </form>
    </Form>
  );
}
