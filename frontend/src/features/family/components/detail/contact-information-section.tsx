import { FamilyMemberDetailsCard } from "@/features/family/components/family-member-details-card";
import type { FamilyMemberDetail } from "@/lib/mock/family-members";

export function ContactInformationSection({ member }: { member: FamilyMemberDetail }) {
  return (
    <FamilyMemberDetailsCard
      title="Contact Information"
      fields={[
        { label: "Email", value: member.email },
        { label: "Phone", value: member.phone },
      ]}
    />
  );
}
