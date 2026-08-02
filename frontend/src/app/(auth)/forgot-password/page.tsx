"use client";

import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { KeyRound } from "lucide-react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { AuthButton } from "@/components/auth/auth-button";
import { AuthCard } from "@/components/auth/auth-card";
import { AuthForm } from "@/components/auth/auth-form";
import { ErrorAlert } from "@/components/auth/error-alert";
import { SuccessAlert } from "@/components/auth/success-alert";
import { FormInput } from "@/components/shared/forms/form-input";
import { ApiError, httpClient } from "@/lib/api-client";

const forgotPasswordSchema = z.object({
  email: z.string().min(1, "Email is required").email("Enter a valid email address"),
});

type ForgotPasswordValues = z.infer<typeof forgotPasswordSchema>;

export default function ForgotPasswordPage() {
  const [formError, setFormError] = useState<string | null>(null);
  const [submittedEmail, setSubmittedEmail] = useState<string | null>(null);

  const form = useForm<ForgotPasswordValues>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: "" },
  });

  // `POST /auth/forgot-password` is not implemented server-side yet — the
  // same documented, honest gap as every other form in this module. Once
  // it exists, it should follow the standard anti-enumeration pattern
  // (always respond success, regardless of whether the email matches an
  // account) — that's a backend response-shape decision, not something
  // faked here client-side; this page shows whatever the API genuinely
  // returns.
  const forgotPasswordMutation = useMutation({
    mutationFn: (values: ForgotPasswordValues) => httpClient.post("/auth/forgot-password", values),
    onSuccess: (_response, values) => {
      setFormError(null);
      setSubmittedEmail(values.email);
    },
    onError: (error) => {
      setFormError(
        error instanceof ApiError ? error.message : "Unable to send reset instructions.",
      );
    },
  });

  if (submittedEmail) {
    return (
      <AuthCard icon={KeyRound} title="Check your email">
        <SuccessAlert
          title="Reset link sent"
          message={`If an account exists for ${submittedEmail}, we've sent instructions to reset your password.`}
        />
        <p className="mt-4 text-center text-sm text-muted-foreground">
          <Link href="/login" className="font-medium text-primary hover:underline">
            Back to sign in
          </Link>
        </p>
      </AuthCard>
    );
  }

  return (
    <AuthCard
      icon={KeyRound}
      title="Forgot password?"
      description="Enter your email and we'll send you a link to reset your password."
      footer={
        <p className="text-center text-sm text-muted-foreground">
          Remembered your password?{" "}
          <Link href="/login" className="font-medium text-primary hover:underline">
            Back to sign in
          </Link>
        </p>
      }
    >
      <AuthForm
        form={form}
        onSubmit={(values) => {
          setFormError(null);
          forgotPasswordMutation.mutate(values);
        }}
      >
        <ErrorAlert message={formError} />
        <FormInput
          control={form.control}
          name="email"
          label="Email"
          type="email"
          placeholder="you@example.com"
          autoComplete="email"
        />
        <AuthButton loading={forgotPasswordMutation.isPending}>
          {forgotPasswordMutation.isPending ? "Sending..." : "Send reset link"}
        </AuthButton>
      </AuthForm>
    </AuthCard>
  );
}
