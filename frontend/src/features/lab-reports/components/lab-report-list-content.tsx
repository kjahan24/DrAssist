"use client";

import { useMemo, useState } from "react";
import type { SortingState } from "@tanstack/react-table";
import { FlaskConical } from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/dashboard/page-header";
import { DataTablePagination } from "@/components/shared/data-table/data-table-pagination";
import { CardSkeleton } from "@/components/shared/states/card-skeleton";
import { Button } from "@/components/ui/button";
import { LabReportCard } from "@/features/lab-reports/components/lab-report-card";
import { LabReportEmptyState } from "@/features/lab-reports/components/lab-report-empty-state";
import { LabReportFilters } from "@/features/lab-reports/components/lab-report-filters";
import { LabReportSearch } from "@/features/lab-reports/components/lab-report-search";
import { LabReportTable } from "@/features/lab-reports/components/lab-report-table";
import { useLabReports } from "@/features/lab-reports/hooks/use-lab-reports";
import { useDebounce } from "@/hooks/use-debounce";
import type { LabReportCategory, LabReportStatus } from "@/lib/mock/lab-reports";

const PAGE_SIZE = 10;

type SortField =
  "report_number" | "patient_name" | "doctor_name" | "ordered_at" | "collected_at" | "status";

function resolveSortField(columnId: string): SortField {
  if (columnId === "patient") return "patient_name";
  if (columnId === "doctor") return "doctor_name";
  if (columnId === "collected") return "collected_at";
  if (columnId === "status") return "status";
  return "report_number";
}

export function LabReportListContent() {
  const [searchInput, setSearchInput] = useState("");
  const [status, setStatus] = useState<LabReportStatus | "all">("all");
  const [category, setCategory] = useState<LabReportCategory | "all">("all");
  const [sorting, setSorting] = useState<SortingState>([{ id: "collected", desc: true }]);
  const [pageIndex, setPageIndex] = useState(0);

  const debouncedSearch = useDebounce(searchInput, 300);
  const activeSort = sorting[0];

  const params = useMemo(
    () => ({
      search: debouncedSearch,
      status,
      category,
      sortBy: activeSort ? resolveSortField(activeSort.id) : ("ordered_at" as const),
      sortDirection: activeSort?.desc ? ("desc" as const) : ("asc" as const),
      page: pageIndex + 1,
      pageSize: PAGE_SIZE,
    }),
    [debouncedSearch, status, category, activeSort, pageIndex],
  );

  const { data, isLoading, isFetching } = useLabReports(params);

  const hasAnyFilter = Boolean(debouncedSearch) || status !== "all" || category !== "all";
  const showEmptyState = !isLoading && (data?.items.length ?? 0) === 0;

  function handleSortingChange(updater: SortingState | ((old: SortingState) => SortingState)) {
    setSorting((old) => (typeof updater === "function" ? updater(old) : updater));
    setPageIndex(0);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Lab Reports"
        description="Order and review laboratory tests and results."
        actions={
          <Button asChild>
            <Link href="/dashboard/lab-reports/new">
              <FlaskConical className="size-4" />
              New Lab Report
            </Link>
          </Button>
        }
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <LabReportSearch
          value={searchInput}
          onChange={(value) => {
            setSearchInput(value);
            setPageIndex(0);
          }}
        />
        <LabReportFilters
          status={status}
          onStatusChange={(value) => {
            setStatus(value);
            setPageIndex(0);
          }}
          category={category}
          onCategoryChange={(value) => {
            setCategory(value);
            setPageIndex(0);
          }}
        />
      </div>

      {showEmptyState ? (
        <LabReportEmptyState variant={hasAnyFilter ? "no-results" : "empty"} />
      ) : (
        <>
          <LabReportTable
            reports={data?.items ?? []}
            isLoading={isLoading || isFetching}
            sorting={sorting}
            onSortingChange={handleSortingChange}
          />

          <div className="grid gap-3 md:hidden">
            {isLoading
              ? Array.from({ length: 4 }).map((_, index) => <CardSkeleton key={index} />)
              : (data?.items ?? []).map((report) => (
                  <LabReportCard key={report.lab_report_id} report={report} />
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
