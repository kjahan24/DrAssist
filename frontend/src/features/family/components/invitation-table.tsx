"use client";

import type { OnChangeFn, SortingState } from "@tanstack/react-table";

import { DataTable } from "@/components/shared/data-table/data-table";
import { invitationColumns } from "@/features/family/components/invitation-columns";
import type { FamilyMember } from "@/lib/mock/family-invitations";

interface InvitationTableProps {
  invitations: FamilyMember[];
  isLoading?: boolean;
  sorting: SortingState;
  onSortingChange: OnChangeFn<SortingState>;
}

// Desktop-only (hidden below `md`) — `FamilyMemberCard` is reused as the
// mobile counterpart on the Invitations page too (see
// `InvitationListContent`): Resend/Cancel stay reachable from its "View
// Details" link rather than duplicating those actions in a second card
// component.
export function InvitationTable({
  invitations,
  isLoading,
  sorting,
  onSortingChange,
}: InvitationTableProps) {
  return (
    <div className="hidden md:block">
      <DataTable
        columns={invitationColumns}
        data={invitations}
        isLoading={isLoading}
        emptyMessage="No invitations match your search."
        sorting={sorting}
        onSortingChange={onSortingChange}
      />
    </div>
  );
}
