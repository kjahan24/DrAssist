"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { MoreHorizontal } from "lucide-react";
import Link from "next/link";

import { PatientRow } from "@/features/patients/components/patient-row";
import { PatientStatusBadge } from "@/features/patients/components/patient-status-badge";
import { DataTableColumnHeader } from "@/components/shared/data-table/data-table-column-header";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { formatDate } from "@/lib/format";
import { getAge, getFullName, type Patient } from "@/lib/mock/patients";

// Column labels for `PatientColumnVisibilityToggle` — kept alongside the
// column defs since they describe the same columns, just for a UI that
// doesn't have a live TanStack `Table` instance to read `meta` off of.
export const TOGGLEABLE_PATIENT_COLUMNS = [
  { id: "patient_number", label: "Patient ID" },
  { id: "age", label: "Age" },
  { id: "gender", label: "Gender" },
  { id: "phone", label: "Phone" },
  { id: "blood_group", label: "Blood Group" },
  { id: "last_visit_date", label: "Last Visit" },
  { id: "status", label: "Status" },
];

export const patientColumns: ColumnDef<Patient>[] = [
  {
    accessorKey: "patient_number",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Patient ID" />,
    enableSorting: true,
  },
  {
    id: "patient",
    accessorKey: "last_name",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Patient" />,
    cell: ({ row }) => <PatientRow patient={row.original} />,
    enableSorting: true,
    enableHiding: false,
  },
  {
    id: "age",
    header: "Age",
    cell: ({ row }) => `${getAge(row.original.date_of_birth)} yrs`,
    enableSorting: false,
  },
  {
    accessorKey: "gender",
    header: "Gender",
    cell: ({ row }) => <span className="capitalize">{row.original.gender}</span>,
    enableSorting: false,
  },
  {
    accessorKey: "phone",
    header: "Phone",
    enableSorting: false,
  },
  {
    accessorKey: "blood_group",
    header: "Blood Group",
    enableSorting: false,
  },
  {
    accessorKey: "last_visit_date",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Last Visit" />,
    cell: ({ row }) =>
      row.original.last_visit_date ? formatDate(row.original.last_visit_date) : "—",
    enableSorting: true,
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <PatientStatusBadge status={row.original.status} />,
    enableSorting: false,
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
            aria-label={`Actions for ${getFullName(row.original)}`}
          >
            <MoreHorizontal className="size-4" aria-hidden="true" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem asChild>
            <Link href={`/dashboard/patients/${row.original.patient_id}`}>View details</Link>
          </DropdownMenuItem>
          <DropdownMenuItem asChild>
            <Link href={`/dashboard/patients/${row.original.patient_id}/edit`}>Edit patient</Link>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    ),
    enableSorting: false,
    enableHiding: false,
  },
];
