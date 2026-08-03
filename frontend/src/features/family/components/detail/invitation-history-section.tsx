import { SectionCard } from "@/components/dashboard/section-card";
import { InvitationTimeline } from "@/features/family/components/invitation-timeline";
import type { FamilyMemberDetail } from "@/lib/mock/family-members";

export function InvitationHistorySection({ member }: { member: FamilyMemberDetail }) {
  return (
    <SectionCard title="Invitation History">
      <InvitationTimeline entries={member.history} />
    </SectionCard>
  );
}
