"use client";

import { Suspense, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { KeyRound, ShieldAlert } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { AuthButton } from "@/components/auth/auth-button";
import { AuthCard } from "@/components/auth/auth-card";
import { AuthForm } from "@/components/auth/auth-form";
import { ErrorAlert } from "@/components/auth/error-alert";
import { PasswordInput } from "@/components/auth/password-input";
import { PasswordStrengthIndicator } from "@/components/auth/password-strength-indicator";
import { Button } from "@/components/ui/button";
import { ApiError, httpClient } from "@/lib/api-client";
import { passwordSchema } from "@/lib/auth/validation";

const resetPasswordSchema = z
  .object({
    password: passwordSchema,
    confirmPassword: z.string().min(1, "Please confirm your password"),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

type ResetPasswordValues = z.infer<typeof resetPasswordSchema>;

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={null}>
      <ResetPasswordForm />
    </Suspense>
  );
}

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [formError, setFormError] = useState<string | null>(null);

  const form = useForm<ResetPasswordValues>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { password: "", confirmPassword: "" },
  });

  const password = form.watch("password");

  // `POST /auth/reset-password` is not implemented server-side yet — same
  // documented gap as the rest of this module's forms.
  const resetMutation = useMutation({
    mutationFn: (values: ResetPasswordValues) =>
      httpClient.post("/auth/reset-password", { token, password: values.password }),
    onSuccess: () => {
      router.push("/login");
    },
    onError: (error) => {
      setFormError(error instanceof ApiError ? error.message : "Unable to reset your password.");
    },
  });

  // No token in the URL at all is a distinct, checkable-today case — not
  // "the backend rejected it" (which we can't know without the endpoint),
  // just "this link is structurally missing what it needs."
  if (!token) {
    return (
      <AuthCard icon={ShieldAlert} title="Invalid reset link">
        <p className="text-center text-sm text-muted-foreground">
          This password reset link is missing or malformed. Request a new one below.
        </p>
        <Button asChild className="mt-4 w-full">
          <Link href="/forgot-password">Request new link</Link>
        </Button>
      </AuthCard>
    );
  }

  return (
    <AuthCard
      icon={KeyRound}
      title="Reset your password"
      description="Choose a new password for your account."
    >
      <AuthForm
        form={form}
        onSubmit={(values) => {
          setFormError(null);
          resetMutation.mutate(values);
        }}
      >
        <ErrorAlert message={formError} />
        <div className="space-y-2">
          <PasswordInput
            control={form.control}
            name="password"
            label="New Password"
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
        <AuthButton loading={resetMutation.isPending}>
          {resetMutation.isPending ? "Resetting..." : "Reset password"}
        </AuthButton>
      </AuthForm>
    </AuthCard>
  );
}
