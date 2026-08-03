import type { Metadata } from "next";

import { MemberListContent } from "@/features/organization/components/member-list-content";

export const metadata: Metadata = { title: "Organization Members" };

export default function OrganizationMembersPage() {
  return <MemberListContent />;
}
