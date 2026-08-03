import { FamilyMemberDetailsCard } from "@/features/family/components/family-member-details-card";
import { getRelationshipLabel, type FamilyMemberDetail } from "@/lib/mock/family-members";

export function RelationshipSection({ member }: { member: FamilyMemberDetail }) {
  return (
    <FamilyMemberDetailsCard
      title="Relationship"
      fields={[
        { label: "Relationship to Patient", value: getRelationshipLabel(member.relationship) },
      ]}
    />
  );
}
