import type { Metadata } from "next";

import { InvitationListContent } from "@/features/family/components/invitation-list-content";

export const metadata: Metadata = { title: "Invitation Management" };

export default function FamilyInvitationsPage() {
  return <InvitationListContent />;
}
