"use client";

import type { OnChangeFn, SortingState } from "@tanstack/react-table";

import { DataTable } from "@/components/shared/data-table/data-table";
import { prescriptionColumns } from "@/features/prescriptions/components/prescription-columns";
import type { Prescription } from "@/lib/mock/prescriptions";

interface PrescriptionTableProps {
  prescriptions: Prescription[];
  isLoading?: boolean;
  sorting: SortingState;
  onSortingChange: OnChangeFn<SortingState>;
}

// Desktop-only (hidden below `md`) — `PrescriptionCard` is the mobile
// counterpart. Pagination is rendered once by the caller, shared between
// both layouts.
export function PrescriptionTable({
  prescriptions,
  isLoading,
  sorting,
  onSortingChange,
}: PrescriptionTableProps) {
  return (
    <div className="hidden md:block">
      <DataTable
        columns={prescriptionColumns}
        data={prescriptions}
        isLoading={isLoading}
        emptyMessage="No prescriptions match your search."
        sorting={sorting}
        onSortingChange={onSortingChange}
      />
    </div>
  );
}
