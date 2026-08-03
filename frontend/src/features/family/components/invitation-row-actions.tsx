"use client";

import { MoreHorizontal } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  useCancelInvitation,
  useResendInvitation,
} from "@/features/family/hooks/use-family-invitations";
import { useConfirm } from "@/hooks/use-confirm";
import { isFamilyAccessCancellable, type FamilyMember } from "@/lib/mock/family-members";

// A real component (not an inline closure inside a column's `cell`)
// specifically so `useResendInvitation`/`useCancelInvitation`/`useConfirm`
// can be called per-row without breaking the Rules of Hooks — a plain
// function handed to `cell` renders inline in the table body's own
// render pass, not as its own component, so hooks can't safely live
// there directly.
export function InvitationRowActions({ member }: { member: FamilyMember }) {
  const confirm = useConfirm();
  const resendInvitation = useResendInvitation(member.family_access_id);
  const cancelInvitation = useCancelInvitation(member.family_access_id);
  const cancellable = isFamilyAccessCancellable(member.status);

  async function handleResend() {
    await resendInvitation.mutateAsync();
    toast.success(`Invitation resent to ${member.member_name}.`);
  }

  async function handleCancel() {
    const confirmed = await confirm({
      title: "Cancel this invitation?",
      description: `${member.member_name} will no longer be able to accept this invitation. This cannot be undone.`,
      confirmLabel: "Cancel Invitation",
      variant: "destructive",
    });
    if (!confirmed) return;
    await cancelInvitation.mutateAsync();
    toast.success("Invitation cancelled.");
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="size-8"
          aria-label={`Actions for ${member.member_name}`}
        >
          <MoreHorizontal className="size-4" aria-hidden="true" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem asChild>
          <Link href={`/dashboard/family/${member.family_access_id}`}>View details</Link>
        </DropdownMenuItem>
        {cancellable && (
          <>
            <DropdownMenuItem onSelect={handleResend} disabled={resendInvitation.isPending}>
              Resend invitation
            </DropdownMenuItem>
            <DropdownMenuItem
              onSelect={handleCancel}
              disabled={cancelInvitation.isPending}
              className="text-destructive focus:text-destructive"
            >
              Cancel invitation
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
