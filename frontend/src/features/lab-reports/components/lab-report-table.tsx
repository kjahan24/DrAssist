"use client";

import type { OnChangeFn, SortingState } from "@tanstack/react-table";

import { DataTable } from "@/components/shared/data-table/data-table";
import { labReportColumns } from "@/features/lab-reports/components/lab-report-columns";
import type { LabReport } from "@/lib/mock/lab-reports";

interface LabReportTableProps {
  reports: LabReport[];
  isLoading?: boolean;
  sorting: SortingState;
  onSortingChange: OnChangeFn<SortingState>;
}

// Desktop-only (hidden below `md`) — `LabReportCard` is the mobile
// counterpart. Pagination is rendered once by the caller, shared between
// both layouts.
export function LabReportTable({
  reports,
  isLoading,
  sorting,
  onSortingChange,
}: LabReportTableProps) {
  return (
    <div className="hidden md:block">
      <DataTable
        columns={labReportColumns}
        data={reports}
        isLoading={isLoading}
        emptyMessage="No lab reports match your search."
        sorting={sorting}
        onSortingChange={onSortingChange}
      />
    </div>
  );
}
