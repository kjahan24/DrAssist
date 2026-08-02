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
import { ClinicalNotePatientIdentity } from "@/features/clinical-notes/components/clinical-note-patient-identity";
import { ClinicalNoteStatusBadge } from "@/features/clinical-notes/components/clinical-note-status-badge";
import { formatDate, formatDateTime } from "@/lib/format";
import { isClinicalNoteEditable, type ClinicalNote } from "@/lib/mock/clinical-notes";

export const clinicalNoteColumns: ColumnDef<ClinicalNote>[] = [
  {
    accessorKey: "note_number",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Note ID" />,
    enableSorting: true,
  },
  {
    id: "patient",
    accessorKey: "patient_name",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Patient" />,
    cell: ({ row }) => <ClinicalNotePatientIdentity note={row.original} />,
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
    id: "created",
    accessorKey: "created_at",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Created Date" />,
    cell: ({ row }) => formatDate(row.original.created_at),
    enableSorting: true,
  },
  {
    id: "updated",
    accessorKey: "updated_at",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Last Updated" />,
    cell: ({ row }) => formatDateTime(row.original.updated_at),
    enableSorting: true,
  },
  {
    id: "status",
    accessorKey: "status",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Status" />,
    cell: ({ row }) => <ClinicalNoteStatusBadge status={row.original.status} />,
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
            aria-label={`Actions for note ${row.original.note_number}`}
          >
            <MoreHorizontal className="size-4" aria-hidden="true" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem asChild>
            <Link href={`/dashboard/clinical-notes/${row.original.clinical_note_id}`}>
              View details
            </Link>
          </DropdownMenuItem>
          {isClinicalNoteEditable(row.original.status) && (
            <DropdownMenuItem asChild>
              <Link href={`/dashboard/clinical-notes/${row.original.clinical_note_id}/edit`}>
                Edit note
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
