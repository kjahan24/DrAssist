import { Clock } from "lucide-react";
import Link from "next/link";

import { AuthCard } from "@/components/auth/auth-card";
import { Button } from "@/components/ui/button";

// Reached from `lib/api-client.ts`'s 401 interceptor when a request that
// *had* a token gets rejected — a real session that genuinely just ended,
// not a generic "please sign in."
export default function SessionExpiredPage() {
  return (
    <AuthCard
      icon={Clock}
      title="Session expired"
      description="You've been signed out for your security. Please sign in again to continue."
    >
      <Button asChild className="w-full">
        <Link href="/login">Sign in again</Link>
      </Button>
    </AuthCard>
  );
}
