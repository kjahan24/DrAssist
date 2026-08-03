import type { Metadata } from "next";

import { InvitationCreateContent } from "@/features/family/components/invitation-create-content";

export const metadata: Metadata = { title: "Invite Family Member" };

export default function NewInvitationPage() {
  return <InvitationCreateContent />;
}
