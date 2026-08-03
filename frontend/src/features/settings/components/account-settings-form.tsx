"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { LoadingButton } from "@/components/auth/loading-button";
import { FormInput } from "@/components/shared/forms/form-input";
import { Form } from "@/components/ui/form";
import { LanguageSelector } from "@/features/settings/components/language-selector";
import { SettingsSection } from "@/features/settings/components/settings-section";
import { TimezoneSelector } from "@/features/settings/components/timezone-selector";
import type { AccountSettings } from "@/lib/mock/settings";

const accountSettingsSchema = z.object({
  first_name: z.string().min(1, "First name is required"),
  last_name: z.string().min(1, "Last name is required"),
  email: z.string().min(1, "Email is required").email("Enter a valid email address"),
  phone: z.string().min(1, "Phone number is required"),
  locale: z.string().min(1, "Select a language"),
  timezone: z.string().min(1, "Select a time zone"),
}) satisfies z.ZodType<AccountSettings>;

interface AccountSettingsFormProps {
  defaultValues: AccountSettings;
  onSubmit: (values: AccountSettings) => void;
  isSubmitting?: boolean;
}

export function AccountSettingsForm({
  defaultValues,
  onSubmit,
  isSubmitting,
}: AccountSettingsFormProps) {
  const form = useForm<AccountSettings>({
    resolver: zodResolver(accountSettingsSchema),
    defaultValues,
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6" noValidate>
        <SettingsSection
          title="Personal Information"
          description="Your name as it appears across DrAssist."
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <FormInput control={form.control} name="first_name" label="First Name" />
            <FormInput control={form.control} name="last_name" label="Last Name" />
          </div>
        </SettingsSection>

        <SettingsSection title="Contact Information">
          <div className="grid gap-4 sm:grid-cols-2">
            <FormInput control={form.control} name="email" label="Email" type="email" />
            <FormInput control={form.control} name="phone" label="Phone" type="tel" />
          </div>
        </SettingsSection>

        <SettingsSection
          title="Regional Settings"
          description="Used to localize dates, times, and content."
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <LanguageSelector control={form.control} name="locale" />
            <TimezoneSelector control={form.control} name="timezone" />
          </div>
        </SettingsSection>

        <div className="flex justify-end">
          <LoadingButton type="submit" loading={isSubmitting}>
            Save Changes
          </LoadingButton>
        </div>
      </form>
    </Form>
  );
}
