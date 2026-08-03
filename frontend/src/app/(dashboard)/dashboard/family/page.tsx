import type { Metadata } from "next";

import { FamilyMemberListContent } from "@/features/family/components/family-member-list-content";

export const metadata: Metadata = { title: "Family & Caregiver Access" };

export default function FamilyPage() {
  return <FamilyMemberListContent />;
}
