"use client";

import type { OnChangeFn, SortingState } from "@tanstack/react-table";

import { DataTable } from "@/components/shared/data-table/data-table";
import { clinicalNoteColumns } from "@/features/clinical-notes/components/clinical-note-columns";
import type { ClinicalNote } from "@/lib/mock/clinical-notes";

interface ClinicalNoteTableProps {
  notes: ClinicalNote[];
  isLoading?: boolean;
  sorting: SortingState;
  onSortingChange: OnChangeFn<SortingState>;
}

// Desktop-only (hidden below `md`) — `ClinicalNoteCard` is the mobile
// counterpart. Pagination is rendered once by the caller, shared between
// both layouts.
export function ClinicalNoteTable({
  notes,
  isLoading,
  sorting,
  onSortingChange,
}: ClinicalNoteTableProps) {
  return (
    <div className="hidden md:block">
      <DataTable
        columns={clinicalNoteColumns}
        data={notes}
        isLoading={isLoading}
        emptyMessage="No clinical notes match your search."
        sorting={sorting}
        onSortingChange={onSortingChange}
      />
    </div>
  );
}
