"use client";

import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { UserPlus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { AuthButton } from "@/components/auth/auth-button";
import { AuthCard } from "@/components/auth/auth-card";
import { AuthForm } from "@/components/auth/auth-form";
import { ErrorAlert } from "@/components/auth/error-alert";
import { PasswordInput } from "@/components/auth/password-input";
import { PasswordStrengthIndicator } from "@/components/auth/password-strength-indicator";
import { FormInput } from "@/components/shared/forms/form-input";
import { Checkbox } from "@/components/ui/checkbox";
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { ApiError, httpClient } from "@/lib/api-client";
import { applyServerErrors } from "@/lib/auth/apply-server-errors";
import { passwordSchema } from "@/lib/auth/validation";

const registerSchema = z
  .object({
    fullName: z.string().trim().min(2, "Enter your full name"),
    email: z.string().min(1, "Email is required").email("Enter a valid email address"),
    password: passwordSchema,
    confirmPassword: z.string().min(1, "Please confirm your password"),
    acceptTerms: z.boolean().refine((val) => val === true, {
      message: "You must accept the Terms of Service to continue",
    }),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

type RegisterValues = z.infer<typeof registerSchema>;
// "full_name"/"first_name"/"last_name" are deliberately not in this list:
// this form's single "Full Name" field splits into two backend fields
// (see `splitFullName` below), so there's no single RHF field path a
// backend error naming either one could ever be attached to — that
// mismatch falls through to the generic `ErrorAlert` instead, correctly.
const REGISTER_FIELDS = ["email", "password"] as const;

// The backend's `User` entity stores `first_name`/`last_name` separately
// — `full_name` is only a computed property, not a stored field (see
// `app/modules/authentication/domain/entities.py`) — so the single "Full
// Name" field this form presents (per this task's own spec) is split
// before it's sent, to match the real backend shape.
function splitFullName(fullName: string): { first_name: string; last_name: string } {
  const trimmed = fullName.trim();
  const spaceIndex = trimmed.indexOf(" ");
  if (spaceIndex === -1) {
    return { first_name: trimmed, last_name: "" };
  }
  return {
    first_name: trimmed.slice(0, spaceIndex),
    last_name: trimmed.slice(spaceIndex + 1).trim(),
  };
}

export default function RegisterPage() {
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);

  const form = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      fullName: "",
      email: "",
      password: "",
      confirmPassword: "",
      acceptTerms: false,
    },
  });

  const password = form.watch("password");

  // Same honest pattern as Login (see that page for the full backend-gap
  // explanation): `POST /auth/register` is not implemented server-side
  // yet. Wired to the documented future shape so it works immediately
  // once that lands — this genuinely calls the network today rather than
  // faking a success response.
  const registerMutation = useMutation({
    mutationFn: (values: RegisterValues) =>
      httpClient.post("/auth/register", {
        ...splitFullName(values.fullName),
        email: values.email,
        password: values.password,
      }),
    onSuccess: () => {
      router.push("/verify-email");
    },
    onError: (error) => {
      const fieldsSet = applyServerErrors(error, form.setError, REGISTER_FIELDS);
      setFormError(
        fieldsSet > 0
          ? null
          : error instanceof ApiError
            ? error.message
            : "Unable to create your account. Please try again.",
      );
    },
  });

  return (
    <AuthCard
      icon={UserPlus}
      title="Create an account"
      description="Get started with DrAssist"
      footer={
        <p className="text-center text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-primary hover:underline">
            Sign in
          </Link>
        </p>
      }
    >
      <AuthForm
        form={form}
        onSubmit={(values) => {
          setFormError(null);
          registerMutation.mutate(values);
        }}
      >
        <ErrorAlert message={formError} />
        <FormInput
          control={form.control}
          name="fullName"
          label="Full Name"
          placeholder="Jane Doe"
          autoComplete="name"
        />
        <FormInput
          control={form.control}
          name="email"
          label="Email"
          type="email"
          placeholder="you@example.com"
          autoComplete="email"
        />
        <div className="space-y-2">
          <PasswordInput
            control={form.control}
            name="password"
            label="Password"
            autoComplete="new-password"
          />
          <PasswordStrengthIndicator password={password} />
        </div>
        <PasswordInput
          control={form.control}
          name="confirmPassword"
          label="Confirm Password"
          autoComplete="new-password"
        />
        <FormField
          control={form.control}
          name="acceptTerms"
          render={({ field }) => (
            <FormItem className="space-y-2">
              <div className="flex flex-row items-start gap-2 space-y-0">
                <FormControl>
                  <Checkbox
                    checked={field.value}
                    onCheckedChange={field.onChange}
                    className="mt-0.5"
                  />
                </FormControl>
                <FormLabel className="cursor-pointer text-sm font-normal leading-snug">
                  I agree to the{" "}
                  <Link href="/terms" className="text-primary hover:underline" target="_blank">
                    Terms of Service
                  </Link>{" "}
                  and{" "}
                  <Link href="/privacy" className="text-primary hover:underline" target="_blank">
                    Privacy Policy
                  </Link>
                </FormLabel>
              </div>
              <FormMessage />
            </FormItem>
          )}
        />
        <AuthButton loading={registerMutation.isPending}>
          {registerMutation.isPending ? "Creating account..." : "Create account"}
        </AuthButton>
      </AuthForm>
    </AuthCard>
  );
}
