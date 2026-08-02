"use client";

import { useMemo, useState } from "react";
import type { SortingState, VisibilityState } from "@tanstack/react-table";
import { UserPlus } from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/dashboard/page-header";
import { DataTablePagination } from "@/components/shared/data-table/data-table-pagination";
import { CardSkeleton } from "@/components/shared/states/card-skeleton";
import { Button } from "@/components/ui/button";
import { PatientCard } from "@/features/patients/components/patient-card";
import { PatientColumnVisibilityToggle } from "@/features/patients/components/patient-column-visibility-toggle";
import { TOGGLEABLE_PATIENT_COLUMNS } from "@/features/patients/components/patient-columns";
import { PatientEmptyState } from "@/features/patients/components/patient-empty-state";
import { PatientFilters } from "@/features/patients/components/patient-filters";
import { PatientSearch } from "@/features/patients/components/patient-search";
import { PatientTable } from "@/features/patients/components/patient-table";
import { usePatients } from "@/features/patients/hooks/use-patients";
import { useDebounce } from "@/hooks/use-debounce";
import type { Gender, Patient, PatientStatus } from "@/lib/mock/patients";

const PAGE_SIZE = 10;

function resolveSortField(columnId: string): keyof Patient {
  return columnId === "patient" ? "last_name" : (columnId as keyof Patient);
}

export function PatientListContent() {
  const [searchInput, setSearchInput] = useState("");
  const [status, setStatus] = useState<PatientStatus | "all">("all");
  const [gender, setGender] = useState<Gender | "all">("all");
  const [sorting, setSorting] = useState<SortingState>([{ id: "patient", desc: false }]);
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});
  const [pageIndex, setPageIndex] = useState(0);

  const debouncedSearch = useDebounce(searchInput, 300);
  const activeSort = sorting[0];

  const params = useMemo(
    () => ({
      search: debouncedSearch,
      status,
      gender,
      sortBy: activeSort ? resolveSortField(activeSort.id) : ("last_name" as const),
      sortDirection: activeSort?.desc ? ("desc" as const) : ("asc" as const),
      page: pageIndex + 1,
      pageSize: PAGE_SIZE,
    }),
    [debouncedSearch, status, gender, activeSort, pageIndex],
  );

  const { data, isLoading, isFetching } = usePatients(params);

  const hasAnyFilter = Boolean(debouncedSearch) || status !== "all" || gender !== "all";
  const showEmptyState = !isLoading && (data?.items.length ?? 0) === 0;

  function handleSortingChange(updater: SortingState | ((old: SortingState) => SortingState)) {
    setSorting((old) => (typeof updater === "function" ? updater(old) : updater));
    setPageIndex(0);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Patients"
        description="Manage your organization's patient records."
        actions={
          <Button asChild>
            <Link href="/dashboard/patients/new">
              <UserPlus className="size-4" />
              Add Patient
            </Link>
          </Button>
        }
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <PatientSearch
          value={searchInput}
          onChange={(value) => {
            setSearchInput(value);
            setPageIndex(0);
          }}
        />
        <div className="flex items-center gap-2">
          <PatientFilters
            status={status}
            onStatusChange={(value) => {
              setStatus(value);
              setPageIndex(0);
            }}
            gender={gender}
            onGenderChange={(value) => {
              setGender(value);
              setPageIndex(0);
            }}
          />
          <PatientColumnVisibilityToggle
            columns={TOGGLEABLE_PATIENT_COLUMNS}
            columnVisibility={columnVisibility}
            onColumnVisibilityChange={setColumnVisibility}
          />
        </div>
      </div>

      {showEmptyState ? (
        <PatientEmptyState variant={hasAnyFilter ? "no-results" : "empty"} />
      ) : (
        <>
          <PatientTable
            patients={data?.items ?? []}
            isLoading={isLoading || isFetching}
            sorting={sorting}
            onSortingChange={handleSortingChange}
            columnVisibility={columnVisibility}
            onColumnVisibilityChange={setColumnVisibility}
          />

          <div className="grid gap-3 md:hidden">
            {isLoading
              ? Array.from({ length: 4 }).map((_, index) => <CardSkeleton key={index} />)
              : (data?.items ?? []).map((patient) => (
                  <PatientCard key={patient.patient_id} patient={patient} />
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
