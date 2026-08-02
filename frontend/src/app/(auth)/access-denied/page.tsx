import { ShieldX } from "lucide-react";
import Link from "next/link";

import { AuthCard } from "@/components/auth/auth-card";
import { Button } from "@/components/ui/button";

// 403 — the user *is* authenticated but lacks the permission a
// role-gated route requires. No dashboard route redirects here yet
// (dashboard pages are out of scope for this module), but it's ready for
// the first one that does.
export default function AccessDeniedPage() {
  return (
    <AuthCard
      icon={ShieldX}
      title="Access denied"
      description="You don't have permission to access this page. Contact your administrator if you believe this is a mistake."
    >
      <Button asChild className="w-full">
        <Link href="/dashboard">Back to dashboard</Link>
      </Button>
    </AuthCard>
  );
}
