"use client";

import type { OnChangeFn, SortingState, VisibilityState } from "@tanstack/react-table";

import { DataTable } from "@/components/shared/data-table/data-table";
import { patientColumns } from "@/features/patients/components/patient-columns";
import type { Patient } from "@/lib/mock/patients";

interface PatientTableProps {
  patients: Patient[];
  isLoading?: boolean;
  sorting: SortingState;
  onSortingChange: OnChangeFn<SortingState>;
  columnVisibility: VisibilityState;
  onColumnVisibilityChange: OnChangeFn<VisibilityState>;
}

// Desktop-only (hidden below `md`) — `PatientCard` is the mobile
// counterpart. Pagination is rendered once by the caller, shared between
// both layouts, rather than duplicated inside each.
export function PatientTable({
  patients,
  isLoading,
  sorting,
  onSortingChange,
  columnVisibility,
  onColumnVisibilityChange,
}: PatientTableProps) {
  return (
    <div className="hidden md:block">
      <DataTable
        columns={patientColumns}
        data={patients}
        isLoading={isLoading}
        emptyMessage="No patients match your search."
        sorting={sorting}
        onSortingChange={onSortingChange}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={onColumnVisibilityChange}
      />
    </div>
  );
}
