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
import { VisitPatientIdentity } from "@/features/visits/components/visit-patient-identity";
import { VisitStatusBadge } from "@/features/visits/components/visit-status-badge";
import { formatDate } from "@/lib/format";
import { getVisitTypeLabel, type Visit } from "@/lib/mock/visits";

export const visitColumns: ColumnDef<Visit>[] = [
  {
    accessorKey: "visit_number",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Visit ID" />,
    enableSorting: false,
  },
  {
    id: "patient",
    accessorKey: "patient_name",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Patient" />,
    cell: ({ row }) => <VisitPatientIdentity visit={row.original} />,
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
    id: "date",
    accessorKey: "visit_date",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Visit Date" />,
    cell: ({ row }) => formatDate(row.original.visit_date),
    enableSorting: true,
  },
  {
    accessorKey: "visit_type",
    header: "Visit Type",
    cell: ({ row }) => getVisitTypeLabel(row.original.visit_type),
    enableSorting: false,
  },
  {
    id: "chief_complaint",
    accessorKey: "chief_complaint_summary",
    header: "Chief Complaint",
    cell: ({ row }) => (
      <span className="block max-w-[220px] truncate">
        {row.original.chief_complaint_summary || "—"}
      </span>
    ),
    enableSorting: false,
  },
  {
    id: "status",
    accessorKey: "visit_status",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Status" />,
    cell: ({ row }) => <VisitStatusBadge status={row.original.visit_status} />,
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
            aria-label={`Actions for visit ${row.original.visit_number}`}
          >
            <MoreHorizontal className="size-4" aria-hidden="true" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem asChild>
            <Link href={`/dashboard/visits/${row.original.visit_id}`}>View details</Link>
          </DropdownMenuItem>
          <DropdownMenuItem asChild>
            <Link href={`/dashboard/visits/${row.original.visit_id}/edit`}>Edit visit</Link>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    ),
    enableSorting: false,
    enableHiding: false,
  },
];
