"use client";

import { SectionCard } from "@/components/dashboard/section-card";
import { useAuth } from "@/hooks/use-auth";

// Every field here comes from the JWT-derived principal already held in
// client state (`store/auth-store.ts`) — no new network call, no
// fabricated data. Genuinely real, just narrow: `AuthenticatedPrincipal`
// (`types/index.ts`) only carries identity + effective permissions, not
// a full user profile — see that type's own docstring for why.
export function ProfileDetails() {
  const { principal } = useAuth();

  if (!principal) return null;

  return (
    <SectionCard title="Account details" description="Information from your current session.">
      <dl className="grid gap-4 sm:grid-cols-2">
        <div>
          <dt className="text-sm text-muted-foreground">Email</dt>
          <dd className="text-sm font-medium">{principal.email}</dd>
        </div>
        <div>
          <dt className="text-sm text-muted-foreground">User ID</dt>
          <dd className="truncate text-sm font-medium">{principal.user_id}</dd>
        </div>
        <div>
          <dt className="text-sm text-muted-foreground">Organization ID</dt>
          <dd className="truncate text-sm font-medium">{principal.organization_id}</dd>
        </div>
        <div>
          <dt className="text-sm text-muted-foreground">Permissions</dt>
          <dd className="text-sm font-medium">{principal.permissions.length} granted</dd>
        </div>
      </dl>
    </SectionCard>
  );
}
