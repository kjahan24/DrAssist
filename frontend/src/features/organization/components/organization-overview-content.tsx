"use client";

import { Pencil } from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/dashboard/page-header";
import { PageSkeleton } from "@/components/dashboard/page-skeleton";
import { Button } from "@/components/ui/button";
import { OrganizationCard } from "@/features/organization/components/organization-card";
import { useOrganization } from "@/features/organization/hooks/use-organization";

export function OrganizationOverviewContent() {
  const { data: organization, isLoading } = useOrganization();

  if (isLoading || !organization) {
    return <PageSkeleton title="Organization" />;
  }

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader
        title="Organization"
        description="Your organization's public profile and administrative details."
        actions={
          <Button asChild>
            <Link href="/dashboard/organization/edit">
              <Pencil className="size-4" />
              Edit Organization
            </Link>
          </Button>
        }
      />
      <OrganizationCard organization={organization} />
    </div>
  );
}
