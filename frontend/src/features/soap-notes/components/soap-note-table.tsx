"use client";

import type { OnChangeFn, SortingState } from "@tanstack/react-table";

import { DataTable } from "@/components/shared/data-table/data-table";
import { soapNoteColumns } from "@/features/soap-notes/components/soap-note-columns";
import type { SOAPNote } from "@/lib/mock/soap-notes";

interface SoapNoteTableProps {
  notes: SOAPNote[];
  isLoading?: boolean;
  sorting: SortingState;
  onSortingChange: OnChangeFn<SortingState>;
}

// Desktop-only (hidden below `md`) — `SoapNoteCard` is the mobile
// counterpart. Pagination is rendered once by the caller, shared between
// both layouts.
export function SoapNoteTable({ notes, isLoading, sorting, onSortingChange }: SoapNoteTableProps) {
  return (
    <div className="hidden md:block">
      <DataTable
        columns={soapNoteColumns}
        data={notes}
        isLoading={isLoading}
        emptyMessage="No SOAP notes match your search."
        sorting={sorting}
        onSortingChange={onSortingChange}
      />
    </div>
  );
}
