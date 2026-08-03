"use client";

import { useMemo, useState } from "react";
import type { SortingState } from "@tanstack/react-table";
import { FilePlus2 } from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/dashboard/page-header";
import { DataTablePagination } from "@/components/shared/data-table/data-table-pagination";
import { CardSkeleton } from "@/components/shared/states/card-skeleton";
import { Button } from "@/components/ui/button";
import { PrescriptionCard } from "@/features/prescriptions/components/prescription-card";
import { PrescriptionEmptyState } from "@/features/prescriptions/components/prescription-empty-state";
import { PrescriptionFilters } from "@/features/prescriptions/components/prescription-filters";
import { PrescriptionSearch } from "@/features/prescriptions/components/prescription-search";
import { PrescriptionTable } from "@/features/prescriptions/components/prescription-table";
import { usePrescriptions } from "@/features/prescriptions/hooks/use-prescriptions";
import { useDebounce } from "@/hooks/use-debounce";
import type { PrescriptionStatus } from "@/lib/mock/prescriptions";

const PAGE_SIZE = 10;

type SortField =
  "prescription_number" | "patient_name" | "doctor_name" | "prescription_date" | "status";

function resolveSortField(columnId: string): SortField {
  if (columnId === "patient") return "patient_name";
  if (columnId === "doctor") return "doctor_name";
  if (columnId === "issued") return "prescription_date";
  if (columnId === "status") return "status";
  return "prescription_number";
}

export function PrescriptionListContent() {
  const [searchInput, setSearchInput] = useState("");
  const [status, setStatus] = useState<PrescriptionStatus | "all">("all");
  const [sorting, setSorting] = useState<SortingState>([{ id: "issued", desc: true }]);
  const [pageIndex, setPageIndex] = useState(0);

  const debouncedSearch = useDebounce(searchInput, 300);
  const activeSort = sorting[0];

  const params = useMemo(
    () => ({
      search: debouncedSearch,
      status,
      sortBy: activeSort ? resolveSortField(activeSort.id) : ("prescription_date" as const),
      sortDirection: activeSort?.desc ? ("desc" as const) : ("asc" as const),
      page: pageIndex + 1,
      pageSize: PAGE_SIZE,
    }),
    [debouncedSearch, status, activeSort, pageIndex],
  );

  const { data, isLoading, isFetching } = usePrescriptions(params);

  const hasAnyFilter = Boolean(debouncedSearch) || status !== "all";
  const showEmptyState = !isLoading && (data?.items.length ?? 0) === 0;

  function handleSortingChange(updater: SortingState | ((old: SortingState) => SortingState)) {
    setSorting((old) => (typeof updater === "function" ? updater(old) : updater));
    setPageIndex(0);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Prescriptions"
        description="Write and review patient prescriptions."
        actions={
          <Button asChild>
            <Link href="/dashboard/prescriptions/new">
              <FilePlus2 className="size-4" />
              New Prescription
            </Link>
          </Button>
        }
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <PrescriptionSearch
          value={searchInput}
          onChange={(value) => {
            setSearchInput(value);
            setPageIndex(0);
          }}
        />
        <PrescriptionFilters
          status={status}
          onStatusChange={(value) => {
            setStatus(value);
            setPageIndex(0);
          }}
        />
      </div>

      {showEmptyState ? (
        <PrescriptionEmptyState variant={hasAnyFilter ? "no-results" : "empty"} />
      ) : (
        <>
          <PrescriptionTable
            prescriptions={data?.items ?? []}
            isLoading={isLoading || isFetching}
            sorting={sorting}
            onSortingChange={handleSortingChange}
          />

          <div className="grid gap-3 md:hidden">
            {isLoading
              ? Array.from({ length: 4 }).map((_, index) => <CardSkeleton key={index} />)
              : (data?.items ?? []).map((prescription) => (
                  <PrescriptionCard
                    key={prescription.prescription_id}
                    prescription={prescription}
                  />
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
