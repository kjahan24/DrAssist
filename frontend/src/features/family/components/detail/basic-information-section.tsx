import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FamilyMemberDetailsCard } from "@/features/family/components/family-member-details-card";
import { getAccessLevelLabel, type FamilyMemberDetail } from "@/lib/mock/family-members";

export function BasicInformationSection({ member }: { member: FamilyMemberDetail }) {
  return (
    <FamilyMemberDetailsCard
      title="Basic Information"
      actions={
        <Button variant="outline" size="sm" asChild>
          <Link href={`/dashboard/patients/${member.patient_id}`}>View Patient Record</Link>
        </Button>
      }
      fields={[
        { label: "Member Name", value: member.member_name },
        { label: "Patient", value: `${member.patient_name} (${member.patient_number})` },
        {
          label: "Access Level",
          value: <Badge variant="outline">{getAccessLevelLabel(member.access_level)}</Badge>,
        },
      ]}
    />
  );
}
