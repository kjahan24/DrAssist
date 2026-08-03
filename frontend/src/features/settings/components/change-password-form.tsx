"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { LoadingButton } from "@/components/auth/loading-button";
import { FormInput } from "@/components/shared/forms/form-input";
import { Form } from "@/components/ui/form";
import type { ChangePasswordInput } from "@/lib/mock/settings";

const changePasswordSchema = z
  .object({
    current_password: z.string().min(1, "Current password is required"),
    new_password: z.string().min(8, "Password must be at least 8 characters"),
    confirm_password: z.string().min(1, "Please confirm your new password"),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  }) satisfies z.ZodType<ChangePasswordInput>;

const EMPTY_DEFAULTS: ChangePasswordInput = {
  current_password: "",
  new_password: "",
  confirm_password: "",
};

interface ChangePasswordFormProps {
  onSubmit: (values: ChangePasswordInput) => void;
  isSubmitting?: boolean;
}

// "(UI)" per this task — see `lib/mock/settings.ts`'s own docstring:
// there's no real password hash to compare `current_password` against,
// only the two new-password fields are actually validated.
export function ChangePasswordForm({ onSubmit, isSubmitting }: ChangePasswordFormProps) {
  const form = useForm<ChangePasswordInput>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: EMPTY_DEFAULTS,
  });

  function handleSubmit(values: ChangePasswordInput) {
    onSubmit(values);
    form.reset(EMPTY_DEFAULTS);
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4" noValidate>
        <FormInput
          control={form.control}
          name="current_password"
          label="Current Password"
          type="password"
          autoComplete="current-password"
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <FormInput
            control={form.control}
            name="new_password"
            label="New Password"
            type="password"
            autoComplete="new-password"
          />
          <FormInput
            control={form.control}
            name="confirm_password"
            label="Confirm New Password"
            type="password"
            autoComplete="new-password"
          />
        </div>
        <div className="flex justify-end">
          <LoadingButton type="submit" loading={isSubmitting}>
            Update Password
          </LoadingButton>
        </div>
      </form>
    </Form>
  );
}
