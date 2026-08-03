import type { Metadata } from "next";

import { OrganizationOverviewContent } from "@/features/organization/components/organization-overview-content";

export const metadata: Metadata = { title: "Organization" };

export default function OrganizationPage() {
  return <OrganizationOverviewContent />;
}
