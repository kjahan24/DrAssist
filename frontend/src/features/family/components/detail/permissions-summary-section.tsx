import { Badge } from "@/components/ui/badge";
import { SectionCard } from "@/components/dashboard/section-card";
import { PermissionMatrix } from "@/features/family/components/permission-matrix";
import type { FamilyMemberDetail } from "@/lib/mock/family-members";

export function PermissionsSummarySection({ member }: { member: FamilyMemberDetail }) {
  return (
    <SectionCard
      title="Permissions Summary"
      actions={member.has_custom_permissions ? <Badge variant="secondary">Custom</Badge> : null}
    >
      <PermissionMatrix permissions={member.permissions} />
    </SectionCard>
  );
}
