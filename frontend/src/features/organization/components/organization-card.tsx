import { Building2 } from "lucide-react";

import { SectionCard } from "@/components/dashboard/section-card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { OrganizationStatusBadge } from "@/features/organization/components/organization-status-badge";
import { getTimezoneLabel } from "@/lib/mock/settings";
import { getOrganizationTypeLabel, type Organization } from "@/lib/mock/organization";

function formatAddress(organization: Organization): string {
  const parts = [
    organization.address,
    organization.city,
    organization.state,
    organization.postal_code,
    organization.country,
  ].filter(Boolean);
  return parts.length > 0 ? parts.join(", ") : "—";
}

// The read-only view of the organization's own profile —
// `/dashboard/organization` shows this by default, switching to
// `OrganizationForm` on `/dashboard/organization/edit`.
export function OrganizationCard({ organization }: { organization: Organization }) {
  return (
    <SectionCard title="Organization">
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Avatar className="size-20 rounded-lg">
            {organization.logo_url && <AvatarImage src={organization.logo_url} alt="" />}
            <AvatarFallback className="rounded-lg">
              <Building2 className="size-8 text-muted-foreground" aria-hidden="true" />
            </AvatarFallback>
          </Avatar>
          <div className="space-y-1">
            <p className="text-lg font-semibold">{organization.name}</p>
            <p className="text-sm text-muted-foreground">{organization.legal_name}</p>
            <OrganizationStatusBadge status={organization.is_active ? "active" : "inactive"} />
          </div>
        </div>

        <dl className="grid gap-4 sm:grid-cols-2">
          <div>
            <dt className="text-sm text-muted-foreground">Organization Type</dt>
            <dd className="text-sm font-medium">{getOrganizationTypeLabel(organization.type)}</dd>
          </div>
          <div>
            <dt className="text-sm text-muted-foreground">License Number</dt>
            <dd className="text-sm font-medium">{organization.registration_number ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-sm text-muted-foreground">Email</dt>
            <dd className="text-sm font-medium">{organization.email ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-sm text-muted-foreground">Phone</dt>
            <dd className="text-sm font-medium">{organization.phone ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-sm text-muted-foreground">Website</dt>
            <dd className="text-sm font-medium">{organization.website ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-sm text-muted-foreground">Time Zone</dt>
            <dd className="text-sm font-medium">{getTimezoneLabel(organization.timezone)}</dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-sm text-muted-foreground">Address</dt>
            <dd className="text-sm font-medium">{formatAddress(organization)}</dd>
          </div>
        </dl>
      </div>
    </SectionCard>
  );
}
