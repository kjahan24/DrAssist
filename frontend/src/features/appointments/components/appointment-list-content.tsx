"use client";

import { useMemo, useState } from "react";
import type { SortingState } from "@tanstack/react-table";
import { CalendarDays, CalendarPlus, List } from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/dashboard/page-header";
import { DataTablePagination } from "@/components/shared/data-table/data-table-pagination";
import { CardSkeleton } from "@/components/shared/states/card-skeleton";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AppointmentCalendarPreview } from "@/features/appointments/components/appointment-calendar-preview";
import { AppointmentCard } from "@/features/appointments/components/appointment-card";
import { AppointmentEmptyState } from "@/features/appointments/components/appointment-empty-state";
import { AppointmentFilters } from "@/features/appointments/components/appointment-filters";
import { AppointmentSearch } from "@/features/appointments/components/appointment-search";
import { AppointmentTable } from "@/features/appointments/components/appointment-table";
import { useAppointments } from "@/features/appointments/hooks/use-appointments";
import { useDebounce } from "@/hooks/use-debounce";
import type { AppointmentStatus, AppointmentType } from "@/lib/mock/appointments";

const PAGE_SIZE = 10;
// The calendar/agenda view groups appointments by date rather than
// paging them, so it requests a much larger page instead of paginating —
// see `AppointmentCalendarPreview`'s docstring.
const CALENDAR_PAGE_SIZE = 100;

type SortField = "appointment_date" | "patient_name" | "doctor_name" | "status";

function resolveSortField(columnId: string): SortField {
  if (columnId === "date") return "appointment_date";
  if (columnId === "patient") return "patient_name";
  if (columnId === "doctor") return "doctor_name";
  return "status";
}

export function AppointmentListContent() {
  const [view, setView] = useState<"list" | "calendar">("list");
  const [searchInput, setSearchInput] = useState("");
  const [status, setStatus] = useState<AppointmentStatus | "all">("all");
  const [appointmentType, setAppointmentType] = useState<AppointmentType | "all">("all");
  const [sorting, setSorting] = useState<SortingState>([{ id: "date", desc: false }]);
  const [pageIndex, setPageIndex] = useState(0);

  const debouncedSearch = useDebounce(searchInput, 300);
  const activeSort = sorting[0];

  const params = useMemo(
    () => ({
      search: debouncedSearch,
      status,
      appointmentType,
      sortBy: activeSort ? resolveSortField(activeSort.id) : ("appointment_date" as const),
      sortDirection: activeSort?.desc ? ("desc" as const) : ("asc" as const),
      page: view === "calendar" ? 1 : pageIndex + 1,
      pageSize: view === "calendar" ? CALENDAR_PAGE_SIZE : PAGE_SIZE,
    }),
    [debouncedSearch, status, appointmentType, activeSort, pageIndex, view],
  );

  const { data, isLoading, isFetching } = useAppointments(params);

  const hasAnyFilter = Boolean(debouncedSearch) || status !== "all" || appointmentType !== "all";
  const showEmptyState = !isLoading && (data?.items.length ?? 0) === 0;

  function handleSortingChange(updater: SortingState | ((old: SortingState) => SortingState)) {
    setSorting((old) => (typeof updater === "function" ? updater(old) : updater));
    setPageIndex(0);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Appointments"
        description="Manage your organization's scheduled appointments."
        actions={
          <Button asChild>
            <Link href="/dashboard/appointments/new">
              <CalendarPlus className="size-4" />
              New Appointment
            </Link>
          </Button>
        }
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <AppointmentSearch
          value={searchInput}
          onChange={(value) => {
            setSearchInput(value);
            setPageIndex(0);
          }}
        />
        <div className="flex flex-wrap items-center gap-2">
          <AppointmentFilters
            status={status}
            onStatusChange={(value) => {
              setStatus(value);
              setPageIndex(0);
            }}
            appointmentType={appointmentType}
            onAppointmentTypeChange={(value) => {
              setAppointmentType(value);
              setPageIndex(0);
            }}
          />
          <Tabs value={view} onValueChange={(value) => setView(value as "list" | "calendar")}>
            <TabsList>
              <TabsTrigger value="list" aria-label="List view">
                <List className="size-4" />
                <span className="hidden sm:inline">List</span>
              </TabsTrigger>
              <TabsTrigger value="calendar" aria-label="Calendar view">
                <CalendarDays className="size-4" />
                <span className="hidden sm:inline">Calendar</span>
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      </div>

      {showEmptyState ? (
        <AppointmentEmptyState variant={hasAnyFilter ? "no-results" : "empty"} />
      ) : view === "calendar" ? (
        <AppointmentCalendarPreview
          appointments={data?.items ?? []}
          isLoading={isLoading || isFetching}
        />
      ) : (
        <>
          <AppointmentTable
            appointments={data?.items ?? []}
            isLoading={isLoading || isFetching}
            sorting={sorting}
            onSortingChange={handleSortingChange}
          />

          <div className="grid gap-3 md:hidden">
            {isLoading
              ? Array.from({ length: 4 }).map((_, index) => <CardSkeleton key={index} />)
              : (data?.items ?? []).map((appointment) => (
                  <AppointmentCard key={appointment.appointment_id} appointment={appointment} />
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
