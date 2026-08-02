"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { MoreHorizontal } from "lucide-react";
import Link from "next/link";

import { DataTableColumnHeader } from "@/components/shared/data-table/data-table-column-header";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { AppointmentPatientIdentity } from "@/features/appointments/components/appointment-patient-identity";
import { AppointmentStatusBadge } from "@/features/appointments/components/appointment-status-badge";
import { formatDate, formatTime } from "@/lib/format";
import { getTypeLabel, type Appointment } from "@/lib/mock/appointments";

export const appointmentColumns: ColumnDef<Appointment>[] = [
  {
    accessorKey: "appointment_number",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Appointment ID" />,
    enableSorting: false,
  },
  {
    id: "patient",
    accessorKey: "patient_name",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Patient" />,
    cell: ({ row }) => <AppointmentPatientIdentity appointment={row.original} />,
    enableSorting: true,
    enableHiding: false,
  },
  {
    id: "doctor",
    accessorKey: "doctor_name",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Doctor" />,
    enableSorting: true,
  },
  {
    accessorKey: "department",
    header: "Department",
    enableSorting: false,
  },
  {
    id: "date",
    accessorKey: "appointment_date",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Date" />,
    cell: ({ row }) => formatDate(row.original.appointment_date),
    enableSorting: true,
  },
  {
    id: "time",
    header: "Time",
    cell: ({ row }) =>
      `${formatTime(row.original.start_time)} – ${formatTime(row.original.end_time)}`,
    enableSorting: false,
  },
  {
    accessorKey: "appointment_type",
    header: "Visit Type",
    cell: ({ row }) => getTypeLabel(row.original.appointment_type),
    enableSorting: false,
  },
  {
    id: "status",
    accessorKey: "status",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Status" />,
    cell: ({ row }) => <AppointmentStatusBadge status={row.original.status} />,
    enableSorting: true,
  },
  {
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="size-8"
            aria-label={`Actions for appointment ${row.original.appointment_number}`}
          >
            <MoreHorizontal className="size-4" aria-hidden="true" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem asChild>
            <Link href={`/dashboard/appointments/${row.original.appointment_id}`}>
              View details
            </Link>
          </DropdownMenuItem>
          <DropdownMenuItem asChild>
            <Link href={`/dashboard/appointments/${row.original.appointment_id}/edit`}>
              Edit appointment
            </Link>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    ),
    enableSorting: false,
    enableHiding: false,
  },
];
