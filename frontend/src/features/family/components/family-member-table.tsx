"use client";

import type { OnChangeFn, SortingState } from "@tanstack/react-table";

import { DataTable } from "@/components/shared/data-table/data-table";
import { familyMemberColumns } from "@/features/family/components/family-member-columns";
import type { FamilyMember } from "@/lib/mock/family-members";

interface FamilyMemberTableProps {
  members: FamilyMember[];
  isLoading?: boolean;
  sorting: SortingState;
  onSortingChange: OnChangeFn<SortingState>;
}

// Desktop-only (hidden below `md`) — `FamilyMemberCard` is the mobile
// counterpart. Pagination is rendered once by the caller, shared between
// both layouts.
export function FamilyMemberTable({
  members,
  isLoading,
  sorting,
  onSortingChange,
}: FamilyMemberTableProps) {
  return (
    <div className="hidden md:block">
      <DataTable
        columns={familyMemberColumns}
        data={members}
        isLoading={isLoading}
        emptyMessage="No family members match your search."
        sorting={sorting}
        onSortingChange={onSortingChange}
      />
    </div>
  );
}
