import { FamilyMemberDetailsCard } from "@/features/family/components/family-member-details-card";
import { formatDateTime } from "@/lib/format";
import { getFamilyAccessStatusLabel, type FamilyMemberDetail } from "@/lib/mock/family-members";

export function AuditSummarySection({ member }: { member: FamilyMemberDetail }) {
  const lastChange = member.history[member.history.length - 1];

  return (
    <FamilyMemberDetailsCard
      title="Audit Summary"
      fields={[
        { label: "Invited By", value: member.invited_by_name },
        { label: "Invited On", value: formatDateTime(member.invited_at) },
        {
          label: "Last Status Change",
          value: lastChange
            ? `${getFamilyAccessStatusLabel(lastChange.status)} · ${formatDateTime(lastChange.changed_at)}`
            : null,
        },
        { label: "Notes", value: member.notes },
      ]}
    />
  );
}
