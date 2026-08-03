import type { Metadata } from "next";

import { OrganizationEditContent } from "@/features/organization/components/organization-edit-content";

export const metadata: Metadata = { title: "Edit Organization" };

export default function OrganizationEditPage() {
  return <OrganizationEditContent />;
}
