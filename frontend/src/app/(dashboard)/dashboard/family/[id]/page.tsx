import type { Metadata } from "next";

import { FamilyMemberDetailContent } from "@/features/family/components/family-member-detail-content";

export const metadata: Metadata = { title: "Family Member Details" };

export default async function FamilyMemberDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <FamilyMemberDetailContent familyAccessId={id} />;
}
