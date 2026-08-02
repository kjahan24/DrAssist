"use client";

import { Suspense, useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { CheckCircle2 } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

import { AuthCard } from "@/components/auth/auth-card";
import { Button } from "@/components/ui/button";
import { httpClient } from "@/lib/api-client";

export default function VerifyEmailSuccessPage() {
  return (
    <Suspense fallback={null}>
      <VerifyEmailSuccessContent />
    </Suspense>
  );
}

function VerifyEmailSuccessContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [verified, setVerified] = useState(false);

  // `POST /auth/verify-email` is not implemented server-side yet — same
  // documented gap as the rest of this module. This page performs the
  // real call rather than assuming success: no token, or a failed
  // verification, both redirect to `/verify-email/invalid` instead of
  // ever showing a fabricated success state.
  const verifyMutation = useMutation({
    mutationFn: (verificationToken: string) =>
      httpClient.post("/auth/verify-email", { token: verificationToken }),
    onSuccess: () => setVerified(true),
    onError: () => router.replace("/verify-email/invalid"),
  });

  useEffect(() => {
    if (!token) {
      router.replace("/verify-email/invalid");
      return;
    }
    verifyMutation.mutate(token);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  if (!verified) {
    return (
      <AuthCard title="Verifying your email">
        <p className="text-center text-sm text-muted-foreground">
          Please wait while we confirm your email address...
        </p>
      </AuthCard>
    );
  }

  return (
    <AuthCard icon={CheckCircle2} title="Email verified">
      <p className="text-center text-sm text-muted-foreground">
        Your email address has been verified. You can now sign in to your account.
      </p>
      <Button asChild className="mt-4 w-full">
        <Link href="/login">Continue to sign in</Link>
      </Button>
    </AuthCard>
  );
}
