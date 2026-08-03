"use client";

import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { PageHeader } from "@/components/dashboard/page-header";
import { FamilyInvitationForm } from "@/features/family/components/family-invitation-form";
import { useCreateInvitation } from "@/features/family/hooks/use-family-invitations";
import type { FamilyInviteInput } from "@/lib/mock/family-members";

export function InvitationCreateContent() {
  const router = useRouter();
  const createInvitation = useCreateInvitation();

  function handleSubmit(values: FamilyInviteInput) {
    createInvitation.mutate(values, {
      onSuccess: (member) => {
        toast.success(`Invitation sent to ${member.member_name}.`);
        router.push(`/dashboard/family/${member.family_access_id}`);
      },
      onError: (error) => {
        toast.error(error instanceof Error ? error.message : "Failed to send invitation.");
      },
    });
  }

  return (
    <div className="max-w-4xl space-y-6">
      <PageHeader
        title="Invite Family Member"
        description="Share secure access to a patient's record with a trusted family member or caregiver."
      />
      <FamilyInvitationForm onSubmit={handleSubmit} isSubmitting={createInvitation.isPending} />
    </div>
  );
}
