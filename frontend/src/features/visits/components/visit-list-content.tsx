"use client";

import { useMemo, useState } from "react";
import type { SortingState } from "@tanstack/react-table";
import { ClipboardPlus } from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/dashboard/page-header";
import { DataTablePagination } from "@/components/shared/data-table/data-table-pagination";
import { CardSkeleton } from "@/components/shared/states/card-skeleton";
import { Button } from "@/components/ui/button";
import { VisitCard } from "@/features/visits/components/visit-card";
import { VisitEmptyState } from "@/features/visits/components/visit-empty-state";
import { VisitFilters } from "@/features/visits/components/visit-filters";
import { VisitSearch } from "@/features/visits/components/visit-search";
import { VisitTable } from "@/features/visits/components/visit-table";
import { useVisits } from "@/features/visits/hooks/use-visits";
import { useDebounce } from "@/hooks/use-debounce";
import type { VisitStatus, VisitType } from "@/lib/mock/visits";

const PAGE_SIZE = 10;

type SortField = "visit_date" | "patient_name" | "doctor_name" | "status";

function resolveSortField(columnId: string): SortField {
  if (columnId === "date") return "visit_date";
  if (columnId === "patient") return "patient_name";
  if (columnId === "doctor") return "doctor_name";
  return "status";
}

export function VisitListContent() {
  const [searchInput, setSearchInput] = useState("");
  const [status, setStatus] = useState<VisitStatus | "all">("all");
  const [visitType, setVisitType] = useState<VisitType | "all">("all");
  const [sorting, setSorting] = useState<SortingState>([{ id: "date", desc: true }]);
  const [pageIndex, setPageIndex] = useState(0);

  const debouncedSearch = useDebounce(searchInput, 300);
  const activeSort = sorting[0];

  const params = useMemo(
    () => ({
      search: debouncedSearch,
      status,
      visitType,
      sortBy: activeSort ? resolveSortField(activeSort.id) : ("visit_date" as const),
      sortDirection: activeSort?.desc ? ("desc" as const) : ("asc" as const),
      page: pageIndex + 1,
      pageSize: PAGE_SIZE,
    }),
    [debouncedSearch, status, visitType, activeSort, pageIndex],
  );

  const { data, isLoading, isFetching } = useVisits(params);

  const hasAnyFilter = Boolean(debouncedSearch) || status !== "all" || visitType !== "all";
  const showEmptyState = !isLoading && (data?.items.length ?? 0) === 0;

  function handleSortingChange(updater: SortingState | ((old: SortingState) => SortingState)) {
    setSorting((old) => (typeof updater === "function" ? updater(old) : updater));
    setPageIndex(0);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Visits"
        description="Manage your organization's patient visits."
        actions={
          <Button asChild>
            <Link href="/dashboard/visits/new">
              <ClipboardPlus className="size-4" />
              New Visit
            </Link>
          </Button>
        }
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <VisitSearch
          value={searchInput}
          onChange={(value) => {
            setSearchInput(value);
            setPageIndex(0);
          }}
        />
        <VisitFilters
          status={status}
          onStatusChange={(value) => {
            setStatus(value);
            setPageIndex(0);
          }}
          visitType={visitType}
          onVisitTypeChange={(value) => {
            setVisitType(value);
            setPageIndex(0);
          }}
        />
      </div>

      {showEmptyState ? (
        <VisitEmptyState variant={hasAnyFilter ? "no-results" : "empty"} />
      ) : (
        <>
          <VisitTable
            visits={data?.items ?? []}
            isLoading={isLoading || isFetching}
            sorting={sorting}
            onSortingChange={handleSortingChange}
          />

          <div className="grid gap-3 md:hidden">
            {isLoading
              ? Array.from({ length: 4 }).map((_, index) => <CardSkeleton key={index} />)
              : (data?.items ?? []).map((visit) => (
                  <VisitCard key={visit.visit_id} visit={visit} />
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
