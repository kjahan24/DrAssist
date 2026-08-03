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
import { PrescriptionPatientIdentity } from "@/features/prescriptions/components/prescription-patient-identity";
import { PrescriptionStatusBadge } from "@/features/prescriptions/components/prescription-status-badge";
import { formatDate } from "@/lib/format";
import { isPrescriptionEditable, type Prescription } from "@/lib/mock/prescriptions";

export const prescriptionColumns: ColumnDef<Prescription>[] = [
  {
    accessorKey: "prescription_number",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Prescription ID" />,
    enableSorting: true,
  },
  {
    id: "patient",
    accessorKey: "patient_name",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Patient" />,
    cell: ({ row }) => <PrescriptionPatientIdentity prescription={row.original} />,
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
    id: "visit",
    header: "Visit",
    cell: ({ row }) => (
      <Link
        href={`/dashboard/visits/${row.original.visit_id}`}
        className="text-primary underline-offset-4 hover:underline"
      >
        {row.original.visit_number}
      </Link>
    ),
    enableSorting: false,
  },
  {
    id: "issued",
    accessorKey: "prescription_date",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Issued Date" />,
    cell: ({ row }) => formatDate(row.original.prescription_date),
    enableSorting: true,
  },
  {
    id: "status",
    accessorKey: "status",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Status" />,
    cell: ({ row }) => <PrescriptionStatusBadge status={row.original.status} />,
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
            aria-label={`Actions for prescription ${row.original.prescription_number}`}
          >
            <MoreHorizontal className="size-4" aria-hidden="true" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem asChild>
            <Link href={`/dashboard/prescriptions/${row.original.prescription_id}`}>
              View details
            </Link>
          </DropdownMenuItem>
          {isPrescriptionEditable(row.original.status) && (
            <DropdownMenuItem asChild>
              <Link href={`/dashboard/prescriptions/${row.original.prescription_id}/edit`}>
                Edit prescription
              </Link>
            </DropdownMenuItem>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
    ),
    enableSorting: false,
    enableHiding: false,
  },
];
