import { ShieldAlert } from "lucide-react";
import Link from "next/link";

import { AuthCard } from "@/components/auth/auth-card";
import { Button } from "@/components/ui/button";

export default function InvalidVerificationLinkPage() {
  return (
    <AuthCard
      icon={ShieldAlert}
      title="Invalid verification link"
      description="This verification link is invalid, expired, or has already been used."
    >
      <div className="space-y-2">
        <Button asChild className="w-full">
          <Link href="/verify-email">Request a new link</Link>
        </Button>
        <Button asChild variant="outline" className="w-full">
          <Link href="/login">Back to sign in</Link>
        </Button>
      </div>
    </AuthCard>
  );
}
