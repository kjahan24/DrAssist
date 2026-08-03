"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { LoadingButton } from "@/components/auth/loading-button";
import { SectionCard } from "@/components/dashboard/section-card";
import { FormInput } from "@/components/shared/forms/form-input";
import { FormSelect } from "@/components/shared/forms/form-select";
import { Button } from "@/components/ui/button";
import { Form } from "@/components/ui/form";
import { AvatarUploader } from "@/features/settings/components/avatar-uploader";
import { TimezoneSelector } from "@/features/settings/components/timezone-selector";
import {
  ORGANIZATION_TYPE_OPTIONS,
  type Organization,
  type OrganizationFormInput,
} from "@/lib/mock/organization";

const organizationFormSchema = z.object({
  name: z.string().min(1, "Organization name is required"),
  legal_name: z.string(),
  type: z.enum(["clinic", "hospital", "diagnostic", "telemedicine"]),
  registration_number: z.string(),
  email: z.string().email("Enter a valid email address").or(z.literal("")),
  phone: z.string(),
  website: z.string(),
  address: z.string(),
  city: z.string(),
  state: z.string(),
  country: z.string(),
  postal_code: z.string(),
  timezone: z.string().min(1, "Select a time zone"),
}) satisfies z.ZodType<OrganizationFormInput>;

interface OrganizationFormProps {
  organization: Organization;
  defaultValues: OrganizationFormInput;
  onSubmit: (values: OrganizationFormInput) => void;
  onLogoChange: (logoUrl: string) => void;
  onCancel: () => void;
  isSubmitting?: boolean;
}

// Reuses `AvatarUploader` (Module 17's Profile logo/photo picker) for
// the organization logo instead of a separate `LogoUploader` — same
// "(UI) preview only, nothing uploaded" behavior applies equally well to
// an org logo as a person's avatar, so a second near-identical component
// isn't warranted.
export function OrganizationForm({
  organization,
  defaultValues,
  onSubmit,
  onLogoChange,
  onCancel,
  isSubmitting,
}: OrganizationFormProps) {
  const form = useForm<OrganizationFormInput>({
    resolver: zodResolver(organizationFormSchema),
    defaultValues,
  });

  return (
    <SectionCard title="Edit Organization">
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6" noValidate>
          <AvatarUploader
            name={organization.name}
            avatarUrl={organization.logo_url}
            onChange={onLogoChange}
            disabled={isSubmitting}
          />

          <div className="grid gap-4 sm:grid-cols-2">
            <FormInput control={form.control} name="name" label="Organization Name" />
            <FormInput control={form.control} name="legal_name" label="Legal Name" />
            <FormSelect
              control={form.control}
              name="type"
              label="Organization Type"
              options={ORGANIZATION_TYPE_OPTIONS}
            />
            <FormInput control={form.control} name="registration_number" label="License Number" />
            <FormInput control={form.control} name="email" label="Email" type="email" />
            <FormInput control={form.control} name="phone" label="Phone" type="tel" />
            <FormInput control={form.control} name="website" label="Website" />
            <TimezoneSelector control={form.control} name="timezone" />
            <div className="sm:col-span-2">
              <FormInput control={form.control} name="address" label="Address" />
            </div>
            <FormInput control={form.control} name="city" label="City" />
            <FormInput control={form.control} name="state" label="State / Province" />
            <FormInput control={form.control} name="country" label="Country" />
            <FormInput control={form.control} name="postal_code" label="Postal Code" />
          </div>

          <div className="flex justify-end gap-3">
            <Button type="button" variant="outline" onClick={onCancel} disabled={isSubmitting}>
              Cancel
            </Button>
            <LoadingButton type="submit" loading={isSubmitting}>
              Save Changes
            </LoadingButton>
          </div>
        </form>
      </Form>
    </SectionCard>
  );
}
