"use client";

import { useMemo, useState } from "react";
import type { SortingState } from "@tanstack/react-table";
import { NotebookPen } from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/dashboard/page-header";
import { DataTablePagination } from "@/components/shared/data-table/data-table-pagination";
import { CardSkeleton } from "@/components/shared/states/card-skeleton";
import { Button } from "@/components/ui/button";
import { ClinicalNoteCard } from "@/features/clinical-notes/components/clinical-note-card";
import { ClinicalNoteEmptyState } from "@/features/clinical-notes/components/clinical-note-empty-state";
import { ClinicalNoteFilters } from "@/features/clinical-notes/components/clinical-note-filters";
import { ClinicalNoteSearch } from "@/features/clinical-notes/components/clinical-note-search";
import { ClinicalNoteTable } from "@/features/clinical-notes/components/clinical-note-table";
import { useClinicalNotes } from "@/features/clinical-notes/hooks/use-clinical-notes";
import { useDebounce } from "@/hooks/use-debounce";
import type { ClinicalNoteStatus, ClinicalNoteType } from "@/lib/mock/clinical-notes";

const PAGE_SIZE = 10;

type SortField =
  "note_number" | "patient_name" | "doctor_name" | "created_at" | "updated_at" | "status";

function resolveSortField(columnId: string): SortField {
  if (columnId === "patient") return "patient_name";
  if (columnId === "doctor") return "doctor_name";
  if (columnId === "created") return "created_at";
  if (columnId === "updated") return "updated_at";
  if (columnId === "status") return "status";
  return "note_number";
}

export function ClinicalNoteListContent() {
  const [searchInput, setSearchInput] = useState("");
  const [status, setStatus] = useState<ClinicalNoteStatus | "all">("all");
  const [noteType, setNoteType] = useState<ClinicalNoteType | "all">("all");
  const [sorting, setSorting] = useState<SortingState>([{ id: "created", desc: true }]);
  const [pageIndex, setPageIndex] = useState(0);

  const debouncedSearch = useDebounce(searchInput, 300);
  const activeSort = sorting[0];

  const params = useMemo(
    () => ({
      search: debouncedSearch,
      status,
      noteType,
      sortBy: activeSort ? resolveSortField(activeSort.id) : ("created_at" as const),
      sortDirection: activeSort?.desc ? ("desc" as const) : ("asc" as const),
      page: pageIndex + 1,
      pageSize: PAGE_SIZE,
    }),
    [debouncedSearch, status, noteType, activeSort, pageIndex],
  );

  const { data, isLoading, isFetching } = useClinicalNotes(params);

  const hasAnyFilter = Boolean(debouncedSearch) || status !== "all" || noteType !== "all";
  const showEmptyState = !isLoading && (data?.items.length ?? 0) === 0;

  function handleSortingChange(updater: SortingState | ((old: SortingState) => SortingState)) {
    setSorting((old) => (typeof updater === "function" ? updater(old) : updater));
    setPageIndex(0);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Clinical Notes"
        description="Document and review your organization's clinical encounters."
        actions={
          <Button asChild>
            <Link href="/dashboard/clinical-notes/new">
              <NotebookPen className="size-4" />
              New Clinical Note
            </Link>
          </Button>
        }
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <ClinicalNoteSearch
          value={searchInput}
          onChange={(value) => {
            setSearchInput(value);
            setPageIndex(0);
          }}
        />
        <ClinicalNoteFilters
          status={status}
          onStatusChange={(value) => {
            setStatus(value);
            setPageIndex(0);
          }}
          noteType={noteType}
          onNoteTypeChange={(value) => {
            setNoteType(value);
            setPageIndex(0);
          }}
        />
      </div>

      {showEmptyState ? (
        <ClinicalNoteEmptyState variant={hasAnyFilter ? "no-results" : "empty"} />
      ) : (
        <>
          <ClinicalNoteTable
            notes={data?.items ?? []}
            isLoading={isLoading || isFetching}
            sorting={sorting}
            onSortingChange={handleSortingChange}
          />

          <div className="grid gap-3 md:hidden">
            {isLoading
              ? Array.from({ length: 4 }).map((_, index) => <CardSkeleton key={index} />)
              : (data?.items ?? []).map((note) => (
                  <ClinicalNoteCard key={note.clinical_note_id} note={note} />
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
