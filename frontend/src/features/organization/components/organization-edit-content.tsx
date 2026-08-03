"use client";

import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { PageHeader } from "@/components/dashboard/page-header";
import { PageSkeleton } from "@/components/dashboard/page-skeleton";
import { OrganizationForm } from "@/features/organization/components/organization-form";
import {
  useOrganization,
  useUpdateLogo,
  useUpdateOrganization,
} from "@/features/organization/hooks/use-organization";
import { organizationToFormInput, type OrganizationFormInput } from "@/lib/mock/organization";

export function OrganizationEditContent() {
  const router = useRouter();
  const { data: organization, isLoading } = useOrganization();
  const updateOrganization = useUpdateOrganization();
  const updateLogo = useUpdateLogo();

  if (isLoading || !organization) {
    return <PageSkeleton title="Edit Organization" />;
  }

  function handleSubmit(values: OrganizationFormInput) {
    updateOrganization.mutate(values, {
      onSuccess: () => {
        toast.success("Organization updated.");
        router.push("/dashboard/organization");
      },
    });
  }

  function handleLogoChange(logoUrl: string) {
    updateLogo.mutate(logoUrl);
  }

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader
        title="Edit Organization"
        description={`Update ${organization.name}'s profile.`}
      />
      <OrganizationForm
        organization={organization}
        defaultValues={organizationToFormInput(organization)}
        onSubmit={handleSubmit}
        onLogoChange={handleLogoChange}
        onCancel={() => router.push("/dashboard/organization")}
        isSubmitting={updateOrganization.isPending}
      />
    </div>
  );
}
