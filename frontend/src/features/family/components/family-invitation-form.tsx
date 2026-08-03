"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { LoadingButton } from "@/components/auth/loading-button";
import { FormInput } from "@/components/shared/forms/form-input";
import { FormSelect } from "@/components/shared/forms/form-select";
import { FormTextarea } from "@/components/shared/forms/form-textarea";
import { Form, FormDescription, FormField, FormItem, FormLabel } from "@/components/ui/form";
import { Switch } from "@/components/ui/switch";
import { PatientCombobox } from "@/features/appointments/components/patient-combobox";
import { FamilyFormSection } from "@/features/family/components/family-form-section";
import { PermissionToggleGroup } from "@/features/family/components/permission-toggle-group";
import {
  ACCESS_LEVEL_OPTIONS,
  RELATIONSHIP_OPTIONS,
  getAccessLevelDescription,
  getDefaultPermissions,
  type AccessLevel,
  type FamilyInviteInput,
  type FamilyMemberPermissions,
  type Relationship,
} from "@/lib/mock/family-members";

const RELATIONSHIP_VALUES = RELATIONSHIP_OPTIONS.map((option) => option.value) as [
  Relationship,
  ...Relationship[],
];
const ACCESS_LEVEL_VALUES = ACCESS_LEVEL_OPTIONS.map((option) => option.value) as [
  AccessLevel,
  ...AccessLevel[],
];

const permissionsSchema = z.object({
  patient_profile: z.boolean(),
  appointments: z.boolean(),
  visits: z.boolean(),
  clinical_notes: z.boolean(),
  soap_notes: z.boolean(),
  lab_reports: z.boolean(),
  prescriptions: z.boolean(),
  medical_documents: z.boolean(),
  health_timeline: z.boolean(),
  download_documents: z.boolean(),
}) satisfies z.ZodType<FamilyMemberPermissions>;

const invitationFormSchema = z.object({
  patient_id: z.string().min(1, "Select a patient"),
  member_name: z.string().min(1, "Name is required"),
  email: z.string().min(1, "Email is required").email("Enter a valid email address"),
  phone: z.string().min(1, "Phone number is required"),
  relationship: z.enum(RELATIONSHIP_VALUES),
  access_level: z.enum(ACCESS_LEVEL_VALUES),
  has_custom_permissions: z.boolean(),
  permissions: permissionsSchema,
  notes: z.string(),
}) satisfies z.ZodType<FamilyInviteInput>;

const EMPTY_DEFAULTS: FamilyInviteInput = {
  patient_id: "",
  member_name: "",
  email: "",
  phone: "",
  relationship: "caregiver",
  access_level: "viewer",
  has_custom_permissions: false,
  permissions: getDefaultPermissions("viewer"),
  notes: "",
};

interface FamilyInvitationFormProps {
  onSubmit: (values: FamilyInviteInput) => void;
  isSubmitting?: boolean;
}

// Since the real `InviteCaregiver` use case requires an existing
// `caregiver_user_id` this app has no user-picker for yet (see
// `lib/mock/family-members.ts`'s own docstring), this form collects the
// caregiver's contact identity directly instead of a combobox. Access
// level drives a sensible permission default (`getDefaultPermissions()`)
// that stays in sync automatically until "Custom Permissions" is
// switched on, at which point `PermissionToggleGroup` takes over.
export function FamilyInvitationForm({ onSubmit, isSubmitting }: FamilyInvitationFormProps) {
  const form = useForm<FamilyInviteInput>({
    resolver: zodResolver(invitationFormSchema),
    defaultValues: EMPTY_DEFAULTS,
  });

  const accessLevel = form.watch("access_level");
  const hasCustomPermissions = form.watch("has_custom_permissions");
  const permissions = form.watch("permissions");

  useEffect(() => {
    if (!hasCustomPermissions) {
      form.setValue("permissions", getDefaultPermissions(accessLevel));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessLevel, hasCustomPermissions]);

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6" noValidate>
        <FamilyFormSection title="Patient">
          <PatientCombobox control={form.control} name="patient_id" />
        </FamilyFormSection>

        <FamilyFormSection title="Family Member / Caregiver">
          <FormInput control={form.control} name="member_name" label="Full Name" />
          <FormSelect
            control={form.control}
            name="relationship"
            label="Relationship"
            options={RELATIONSHIP_OPTIONS}
          />
          <FormInput control={form.control} name="email" label="Email" type="email" />
          <FormInput control={form.control} name="phone" label="Phone" type="tel" />
        </FamilyFormSection>

        <FamilyFormSection title="Access Level">
          <div className="sm:col-span-2">
            <FormSelect
              control={form.control}
              name="access_level"
              label="Access Level"
              options={ACCESS_LEVEL_OPTIONS}
            />
            <p className="mt-2 text-sm text-muted-foreground">
              {getAccessLevelDescription(accessLevel)}
            </p>
          </div>

          <div className="sm:col-span-2">
            <FormField
              control={form.control}
              name="has_custom_permissions"
              render={({ field }) => (
                <FormItem className="flex items-center justify-between gap-3 rounded-md border p-3">
                  <div className="space-y-0.5">
                    <FormLabel className="text-sm font-medium">Custom Permissions</FormLabel>
                    <FormDescription>
                      Override the access level&apos;s default permissions individually.
                    </FormDescription>
                  </div>
                  <Switch checked={field.value} onCheckedChange={field.onChange} />
                </FormItem>
              )}
            />
          </div>

          <div className="sm:col-span-2">
            <PermissionToggleGroup
              permissions={permissions}
              disabled={!hasCustomPermissions}
              onChange={(value) => form.setValue("permissions", value)}
            />
          </div>
        </FamilyFormSection>

        <FamilyFormSection title="Notes">
          <div className="sm:col-span-2">
            <FormTextarea control={form.control} name="notes" label="Notes (optional)" rows={3} />
          </div>
        </FamilyFormSection>

        <div className="flex justify-end gap-3">
          <LoadingButton type="submit" loading={isSubmitting}>
            Send Invitation
          </LoadingButton>
        </div>
      </form>
    </Form>
  );
}
