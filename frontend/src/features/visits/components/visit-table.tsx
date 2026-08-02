"use client";

import type { OnChangeFn, SortingState } from "@tanstack/react-table";

import { DataTable } from "@/components/shared/data-table/data-table";
import { visitColumns } from "@/features/visits/components/visit-columns";
import type { Visit } from "@/lib/mock/visits";

interface VisitTableProps {
  visits: Visit[];
  isLoading?: boolean;
  sorting: SortingState;
  onSortingChange: OnChangeFn<SortingState>;
}

// Desktop-only (hidden below `md`) — `VisitCard` is the mobile
// counterpart. Pagination is rendered once by the caller, shared between
// both layouts.
export function VisitTable({ visits, isLoading, sorting, onSortingChange }: VisitTableProps) {
  return (
    <div className="hidden md:block">
      <DataTable
        columns={visitColumns}
        data={visits}
        isLoading={isLoading}
        emptyMessage="No visits match your search."
        sorting={sorting}
        onSortingChange={onSortingChange}
      />
    </div>
  );
}
