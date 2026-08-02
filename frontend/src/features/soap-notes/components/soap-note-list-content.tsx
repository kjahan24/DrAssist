"use client";

import { useMemo, useState } from "react";
import type { SortingState } from "@tanstack/react-table";
import { FilePlus2 } from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/dashboard/page-header";
import { DataTablePagination } from "@/components/shared/data-table/data-table-pagination";
import { CardSkeleton } from "@/components/shared/states/card-skeleton";
import { Button } from "@/components/ui/button";
import { SoapNoteCard } from "@/features/soap-notes/components/soap-note-card";
import { SoapNoteEmptyState } from "@/features/soap-notes/components/soap-note-empty-state";
import { SoapNoteFilters } from "@/features/soap-notes/components/soap-note-filters";
import { SoapNoteSearch } from "@/features/soap-notes/components/soap-note-search";
import { SoapNoteTable } from "@/features/soap-notes/components/soap-note-table";
import { useSoapNotes } from "@/features/soap-notes/hooks/use-soap-notes";
import { useDebounce } from "@/hooks/use-debounce";
import type { SOAPNoteStatus } from "@/lib/mock/soap-notes";

const PAGE_SIZE = 10;

type SortField = "soap_number" | "patient_name" | "doctor_name" | "created_at" | "status";

function resolveSortField(columnId: string): SortField {
  if (columnId === "patient") return "patient_name";
  if (columnId === "doctor") return "doctor_name";
  if (columnId === "created") return "created_at";
  if (columnId === "status") return "status";
  return "soap_number";
}

export function SoapNoteListContent() {
  const [searchInput, setSearchInput] = useState("");
  const [status, setStatus] = useState<SOAPNoteStatus | "all">("all");
  const [sorting, setSorting] = useState<SortingState>([{ id: "created", desc: true }]);
  const [pageIndex, setPageIndex] = useState(0);

  const debouncedSearch = useDebounce(searchInput, 300);
  const activeSort = sorting[0];

  const params = useMemo(
    () => ({
      search: debouncedSearch,
      status,
      sortBy: activeSort ? resolveSortField(activeSort.id) : ("created_at" as const),
      sortDirection: activeSort?.desc ? ("desc" as const) : ("asc" as const),
      page: pageIndex + 1,
      pageSize: PAGE_SIZE,
    }),
    [debouncedSearch, status, activeSort, pageIndex],
  );

  const { data, isLoading, isFetching } = useSoapNotes(params);

  const hasAnyFilter = Boolean(debouncedSearch) || status !== "all";
  const showEmptyState = !isLoading && (data?.items.length ?? 0) === 0;

  function handleSortingChange(updater: SortingState | ((old: SortingState) => SortingState)) {
    setSorting((old) => (typeof updater === "function" ? updater(old) : updater));
    setPageIndex(0);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="SOAP Notes"
        description="Document and review structured clinical encounters."
        actions={
          <Button asChild>
            <Link href="/dashboard/soap-notes/new">
              <FilePlus2 className="size-4" />
              New SOAP Note
            </Link>
          </Button>
        }
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <SoapNoteSearch
          value={searchInput}
          onChange={(value) => {
            setSearchInput(value);
            setPageIndex(0);
          }}
        />
        <SoapNoteFilters
          status={status}
          onStatusChange={(value) => {
            setStatus(value);
            setPageIndex(0);
          }}
        />
      </div>

      {showEmptyState ? (
        <SoapNoteEmptyState variant={hasAnyFilter ? "no-results" : "empty"} />
      ) : (
        <>
          <SoapNoteTable
            notes={data?.items ?? []}
            isLoading={isLoading || isFetching}
            sorting={sorting}
            onSortingChange={handleSortingChange}
          />

          <div className="grid gap-3 md:hidden">
            {isLoading
              ? Array.from({ length: 4 }).map((_, index) => <CardSkeleton key={index} />)
              : (data?.items ?? []).map((note) => (
                  <SoapNoteCard key={note.soap_note_id} note={note} />
                ))}
          </div>

          <DataTablePagination
            pageIndex={pageIndex}
            pageSize={PAGE_SIZE}
            total={data?.total ?? 0}
            onPageChange={setPageIndex}
          />
        </>
      )}
    </div>
  );
}
