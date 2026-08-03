"use client";

import type { OnChangeFn, SortingState } from "@tanstack/react-table";

import { DataTable } from "@/components/shared/data-table/data-table";
import { memberColumns } from "@/features/organization/components/member-columns";
import type { Member } from "@/lib/mock/members";

interface MemberTableProps {
  members: Member[];
  isLoading?: boolean;
  sorting: SortingState;
  onSortingChange: OnChangeFn<SortingState>;
}

// Desktop-only (hidden below `md`) — the members list page's own mobile
// card stack (built inline, see `MemberListContent`) is the counterpart.
export function MemberTable({ members, isLoading, sorting, onSortingChange }: MemberTableProps) {
  return (
    <div className="hidden md:block">
      <DataTable
        columns={memberColumns}
        data={members}
        isLoading={isLoading}
        emptyMessage="No members match your search."
        sorting={sorting}
        onSortingChange={onSortingChange}
      />
    </div>
  );
}
