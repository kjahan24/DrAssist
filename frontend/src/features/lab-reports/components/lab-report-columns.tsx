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
import { LabReportPatientIdentity } from "@/features/lab-reports/components/lab-report-patient-identity";
import { LabReportStatusBadge } from "@/features/lab-reports/components/lab-report-status-badge";
import { formatDate } from "@/lib/format";
import {
  getLabReportCategoryLabel,
  isLabReportEditable,
  type LabReport,
} from "@/lib/mock/lab-reports";

export const labReportColumns: ColumnDef<LabReport>[] = [
  {
    accessorKey: "report_number",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Report ID" />,
    enableSorting: true,
  },
  {
    id: "patient",
    accessorKey: "patient_name",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Patient" />,
    cell: ({ row }) => <LabReportPatientIdentity report={row.original} />,
    enableSorting: true,
    enableHiding: false,
  },
  {
    id: "test_name",
    accessorKey: "test_summary",
    header: "Test Name",
    cell: ({ row }) => (
      <span className="block max-w-[200px] truncate">{row.original.test_summary}</span>
    ),
    enableSorting: false,
  },
  {
    accessorKey: "category",
    header: "Category",
    cell: ({ row }) => getLabReportCategoryLabel(row.original.category),
    enableSorting: false,
  },
  {
    id: "doctor",
    accessorKey: "doctor_name",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Ordered By" />,
    enableSorting: true,
  },
  {
    id: "collected",
    accessorKey: "collected_at",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Collected Date" />,
    cell: ({ row }) => (row.original.collected_at ? formatDate(row.original.collected_at) : "—"),
    enableSorting: true,
  },
  {
    id: "status",
    accessorKey: "status",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Status" />,
    cell: ({ row }) => <LabReportStatusBadge status={row.original.status} />,
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
            aria-label={`Actions for lab report ${row.original.report_number}`}
          >
            <MoreHorizontal className="size-4" aria-hidden="true" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem asChild>
            <Link href={`/dashboard/lab-reports/${row.original.lab_report_id}`}>View details</Link>
          </DropdownMenuItem>
          {isLabReportEditable(row.original.status) && (
            <DropdownMenuItem asChild>
              <Link href={`/dashboard/lab-reports/${row.original.lab_report_id}/edit`}>
                Edit report
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
