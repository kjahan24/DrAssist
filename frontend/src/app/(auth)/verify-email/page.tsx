"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { MailCheck } from "lucide-react";
import Link from "next/link";

import { AuthButton } from "@/components/auth/auth-button";
import { AuthCard } from "@/components/auth/auth-card";
import { ErrorAlert } from "@/components/auth/error-alert";
import { SuccessAlert } from "@/components/auth/success-alert";
import { ApiError, httpClient } from "@/lib/api-client";

// Landing page shown right after Register — check-your-inbox messaging,
// plus a real (not faked) resend action.
export default function VerifyEmailPage() {
  const [formError, setFormError] = useState<string | null>(null);
  const [resent, setResent] = useState(false);

  // `POST /auth/resend-verification` is not implemented server-side yet —
  // same documented gap as the rest of this module's forms.
  const resendMutation = useMutation({
    mutationFn: () => httpClient.post("/auth/resend-verification"),
    onSuccess: () => {
      setFormError(null);
      setResent(true);
    },
    onError: (error) => {
      setFormError(
        error instanceof ApiError ? error.message : "Unable to resend the verification email.",
      );
    },
  });

  return (
    <AuthCard
      icon={MailCheck}
      title="Verify your email"
      description="We've sent a verification link to your email address. Click it to activate your account."
      footer={
        <p className="text-center text-sm text-muted-foreground">
          <Link href="/login" className="font-medium text-primary hover:underline">
            Back to sign in
          </Link>
        </p>
      }
    >
      <div className="space-y-4">
        <ErrorAlert message={formError} />
        <SuccessAlert message={resent ? "We've sent another verification email." : null} />
        <p className="text-center text-sm text-muted-foreground">Didn&apos;t get the email?</p>
        <AuthButton
          type="button"
          variant="outline"
          loading={resendMutation.isPending}
          onClick={() => resendMutation.mutate()}
        >
          {resendMutation.isPending ? "Sending..." : "Resend verification email"}
        </AuthButton>
      </div>
    </AuthCard>
  );
}
