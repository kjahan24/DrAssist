"use client";

import type { OnChangeFn, SortingState } from "@tanstack/react-table";

import { DataTable } from "@/components/shared/data-table/data-table";
import { documentColumns } from "@/features/documents/components/document-columns";
import type { MedicalDocument } from "@/lib/mock/documents";

interface DocumentTableProps {
  documents: MedicalDocument[];
  isLoading?: boolean;
  sorting: SortingState;
  onSortingChange: OnChangeFn<SortingState>;
}

// Desktop-only (hidden below `md`) — `DocumentCard`/`DocumentGrid` are
// the mobile and grid-view counterparts. Pagination is rendered once by
// the caller, shared between all layouts.
export function DocumentTable({
  documents,
  isLoading,
  sorting,
  onSortingChange,
}: DocumentTableProps) {
  return (
    <div className="hidden md:block">
      <DataTable
        columns={documentColumns}
        data={documents}
        isLoading={isLoading}
        emptyMessage="No documents match your search."
        sorting={sorting}
        onSortingChange={onSortingChange}
      />
    </div>
  );
}
