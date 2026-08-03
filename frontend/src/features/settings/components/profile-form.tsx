"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { LoadingButton } from "@/components/auth/loading-button";
import { FormInput } from "@/components/shared/forms/form-input";
import { FormTextarea } from "@/components/shared/forms/form-textarea";
import { Button } from "@/components/ui/button";
import { Form } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AvatarUploader } from "@/features/settings/components/avatar-uploader";
import { SettingsSection } from "@/features/settings/components/settings-section";
import type { DoctorProfile, ProfileFormInput } from "@/lib/mock/profile";

const profileFormSchema = z.object({
  full_name: z.string().min(1, "Full name is required"),
  professional_title: z.string().min(1, "Professional title is required"),
  specialization_name: z.string().min(1, "Specialization is required"),
  email: z.string().min(1, "Email is required").email("Enter a valid email address"),
  phone: z.string().min(1, "Phone number is required"),
  address: z.string().min(1, "Address is required"),
  biography: z.string(),
}) satisfies z.ZodType<ProfileFormInput>;

interface ProfileFormProps {
  profile: DoctorProfile;
  defaultValues: ProfileFormInput;
  onSubmit: (values: ProfileFormInput) => void;
  onAvatarChange: (avatarUrl: string) => void;
  onCancel: () => void;
  isSubmitting?: boolean;
}

// License Number and Organization are shown read-only, not part of the
// submitted form — see `lib/mock/profile.ts`'s own docstring for why
// (both go through distinct, non-self-service backend use cases).
export function ProfileForm({
  profile,
  defaultValues,
  onSubmit,
  onAvatarChange,
  onCancel,
  isSubmitting,
}: ProfileFormProps) {
  const form = useForm<ProfileFormInput>({
    resolver: zodResolver(profileFormSchema),
    defaultValues,
  });

  return (
    <SettingsSection title="Edit Profile">
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6" noValidate>
          <AvatarUploader
            name={profile.full_name}
            avatarUrl={profile.avatar_url}
            onChange={onAvatarChange}
            disabled={isSubmitting}
          />

          <div className="grid gap-4 sm:grid-cols-2">
            <FormInput control={form.control} name="full_name" label="Full Name" />
            <FormInput
              control={form.control}
              name="professional_title"
              label="Professional Title"
            />
            <FormInput control={form.control} name="specialization_name" label="Specialization" />
            <div className="space-y-2">
              <Label htmlFor="profile-license-number">License Number</Label>
              <Input id="profile-license-number" value={profile.license_number} disabled readOnly />
            </div>
            <FormInput control={form.control} name="email" label="Email" type="email" />
            <FormInput control={form.control} name="phone" label="Phone" type="tel" />
            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor="profile-organization">Organization</Label>
              <Input
                id="profile-organization"
                value={profile.organization_name}
                disabled
                readOnly
              />
            </div>
            <div className="sm:col-span-2">
              <FormInput control={form.control} name="address" label="Address" />
            </div>
            <div className="sm:col-span-2">
              <FormTextarea control={form.control} name="biography" label="Biography" rows={4} />
            </div>
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
    </SettingsSection>
  );
}
