import { LogIn } from "lucide-react";
import Link from "next/link";

import { AuthCard } from "@/components/auth/auth-card";
import { Button } from "@/components/ui/button";

// General 401 status page — "you're not signed in at all." Distinct from
// `/session-expired` ("you were signed in, and now aren't").
export default function UnauthorizedPage() {
  return (
    <AuthCard
      icon={LogIn}
      title="Sign in required"
      description="You need to sign in to view this page."
    >
      <Button asChild className="w-full">
        <Link href="/login">Sign in</Link>
      </Button>
    </AuthCard>
  );
}
