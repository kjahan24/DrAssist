import { Badge } from "@/components/ui/badge";
import { getFamilyAccessStatusLabel, type FamilyAccessStatus } from "@/lib/mock/family-members";

const STATUS_VARIANT: Record<
  FamilyAccessStatus,
  "default" | "outline" | "secondary" | "destructive"
> = {
  pending: "outline",
  accepted: "default",
  rejected: "secondary",
  revoked: "destructive",
  expired: "secondary",
};

export function FamilyInvitationStatusBadge({ status }: { status: FamilyAccessStatus }) {
  return <Badge variant={STATUS_VARIANT[status]}>{getFamilyAccessStatusLabel(status)}</Badge>;
}
