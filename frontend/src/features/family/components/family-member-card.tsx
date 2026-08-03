import Link from "next/link";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { FamilyInvitationStatusBadge } from "@/features/family/components/family-invitation-status-badge";
import { formatDate } from "@/lib/format";
import {
  getAccessLevelLabel,
  getRelationshipLabel,
  type FamilyMember,
} from "@/lib/mock/family-members";

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((part) => part[0] ?? "")
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

// The mobile-breakpoint counterpart to `FamilyMemberTable` — shown below
// `md`, where the family list content hides the data table.
export function FamilyMemberCard({ member }: { member: FamilyMember }) {
  return (
    <Card>
      <CardContent className="space-y-3 pt-6">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-3">
            <Avatar className="size-9">
              <AvatarFallback>{getInitials(member.member_name)}</AvatarFallback>
            </Avatar>
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">{member.member_name}</p>
              <p className="truncate text-xs text-muted-foreground">for {member.patient_name}</p>
            </div>
          </div>
          <FamilyInvitationStatusBadge status={member.status} />
        </div>

        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <div>
            <dt className="text-xs text-muted-foreground">Relationship</dt>
            <dd className="truncate">{getRelationshipLabel(member.relationship)}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Access Level</dt>
            <dd className="truncate">
              <Badge variant="outline">{getAccessLevelLabel(member.access_level)}</Badge>
            </dd>
          </div>
          <div className="col-span-2">
            <dt className="text-xs text-muted-foreground">Email</dt>
            <dd className="truncate">{member.email}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Invited</dt>
            <dd>{formatDate(member.invited_at)}</dd>
          </div>
        </dl>

        <div className="flex gap-2 pt-1">
          <Button variant="outline" size="sm" className="flex-1" asChild>
            <Link href={`/dashboard/family/${member.family_access_id}`}>View Details</Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
