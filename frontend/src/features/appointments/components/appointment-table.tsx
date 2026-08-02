"use client";

import type { OnChangeFn, SortingState } from "@tanstack/react-table";

import { DataTable } from "@/components/shared/data-table/data-table";
import { appointmentColumns } from "@/features/appointments/components/appointment-columns";
import type { Appointment } from "@/lib/mock/appointments";

interface AppointmentTableProps {
  appointments: Appointment[];
  isLoading?: boolean;
  sorting: SortingState;
  onSortingChange: OnChangeFn<SortingState>;
}

// Desktop-only (hidden below `md`) — `AppointmentCard` is the mobile
// counterpart. Pagination is rendered once by the caller, shared between
// both layouts.
export function AppointmentTable({
  appointments,
  isLoading,
  sorting,
  onSortingChange,
}: AppointmentTableProps) {
  return (
    <div className="hidden md:block">
      <DataTable
        columns={appointmentColumns}
        data={appointments}
        isLoading={isLoading}
        emptyMessage="No appointments match your search."
        sorting={sorting}
        onSortingChange={onSortingChange}
      />
    </div>
  );
}
