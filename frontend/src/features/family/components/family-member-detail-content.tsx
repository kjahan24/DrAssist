"use client";

import { AlertTriangle, RotateCcw, ShieldOff } from "lucide-react";
import { toast } from "sonner";

import { PageHeader } from "@/components/dashboard/page-header";
import { PageSkeleton } from "@/components/dashboard/page-skeleton";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Button } from "@/components/ui/button";
import { AuditSummarySection } from "@/features/family/components/detail/audit-summary-section";
import { BasicInformationSection } from "@/features/family/components/detail/basic-information-section";
import { ContactInformationSection } from "@/features/family/components/detail/contact-information-section";
import { InvitationHistorySection } from "@/features/family/components/detail/invitation-history-section";
import { PermissionsSummarySection } from "@/features/family/components/detail/permissions-summary-section";
import { RecentActivitySection } from "@/features/family/components/detail/recent-activity-section";
import { RelationshipSection } from "@/features/family/components/detail/relationship-section";
import { FamilyInvitationStatusBadge } from "@/features/family/components/family-invitation-status-badge";
import {
  useCancelInvitation,
  useResendInvitation,
} from "@/features/family/hooks/use-family-invitations";
import { useFamilyMember, useRevokeFamilyMember } from "@/features/family/hooks/use-family-members";
import { useConfirm } from "@/hooks/use-confirm";
import { isFamilyAccessCancellable, isFamilyAccessRevocable } from "@/lib/mock/family-members";

export function FamilyMemberDetailContent({ familyAccessId }: { familyAccessId: string }) {
  const { data: member, isLoading } = useFamilyMember(familyAccessId);
  const confirm = useConfirm();
  const revokeMember = useRevokeFamilyMember(familyAccessId);
  const resendInvitation = useResendInvitation(familyAccessId);
  const cancelInvitation = useCancelInvitation(familyAccessId);

  if (isLoading) {
    return <PageSkeleton title="Family Member" />;
  }

  if (!member) {
    return (
      <EmptyState
        titleAs="h1"
        icon={AlertTriangle}
        title="Family member not found"
        description="This invitation may have been removed, or the link is incorrect."
      />
    );
  }

  const cancellable = isFamilyAccessCancellable(member.status);
  const revocable = isFamilyAccessRevocable(member.status);

  async function handleResend() {
    await resendInvitation.mutateAsync();
    toast.success(`Invitation resent to ${member!.member_name}.`);
  }

  async function handleCancelOrRevoke() {
    const isPending = member!.status === "pending";
    const confirmed = await confirm({
      title: isPending ? "Cancel this invitation?" : "Revoke this member's access?",
      description: isPending
        ? `${member!.member_name} will no longer be able to accept this invitation. This cannot be undone.`
        : `${member!.member_name} will immediately lose access to this patient's record. This cannot be undone.`,
      confirmLabel: isPending ? "Cancel Invitation" : "Revoke Access",
      variant: "destructive",
    });
    if (!confirmed) return;

    if (isPending) {
      await cancelInvitation.mutateAsync();
      toast.success("Invitation cancelled.");
    } else {
      await revokeMember.mutateAsync();
      toast.success("Access revoked.");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={member.member_name}
        description={`Family access for ${member.patient_name} (${member.patient_number})`}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <FamilyInvitationStatusBadge status={member.status} />
            {cancellable && (
              <Button
                variant="outline"
                onClick={handleResend}
                disabled={resendInvitation.isPending}
              >
                <RotateCcw className="size-4" />
                Resend Invitation
              </Button>
            )}
            {revocable && (
              <Button
                variant="destructive"
                onClick={handleCancelOrRevoke}
                disabled={revokeMember.isPending || cancelInvitation.isPending}
              >
                <ShieldOff className="size-4" />
                {cancellable ? "Cancel Invitation" : "Revoke Access"}
              </Button>
            )}
          </div>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <BasicInformationSection member={member} />
        <RelationshipSection member={member} />
        <ContactInformationSection member={member} />
      </div>

      <PermissionsSummarySection member={member} />

      <div className="grid gap-6 lg:grid-cols-2">
        <InvitationHistorySection member={member} />
        <RecentActivitySection member={member} />
      </div>

      <AuditSummarySection member={member} />
    </div>
  );
}
