"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { Download, MoreHorizontal } from "lucide-react";
import Link from "next/link";

import { DataTableColumnHeader } from "@/components/shared/data-table/data-table-column-header";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { DocumentPatientIdentity } from "@/features/documents/components/document-patient-identity";
import { DocumentPreview } from "@/features/documents/components/document-preview";
import { DocumentStatusBadge } from "@/features/documents/components/document-status-badge";
import { showSimulatedDownloadToast } from "@/features/documents/lib/simulated-download";
import { formatDate, formatFileSize } from "@/lib/format";
import {
  getDocumentCategoryLabel,
  isDocumentEditable,
  type MedicalDocument,
} from "@/lib/mock/documents";

export const documentColumns: ColumnDef<MedicalDocument>[] = [
  {
    accessorKey: "document_number",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Document ID" />,
    enableSorting: false,
  },
  {
    id: "patient",
    accessorKey: "patient_name",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Patient" />,
    cell: ({ row }) => <DocumentPatientIdentity document={row.original} />,
    enableSorting: true,
    enableHiding: false,
  },
  {
    id: "title",
    accessorKey: "title",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Document Name" />,
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <DocumentPreview mimeType={row.original.mime_type} extension={row.original.extension} />
        <div className="min-w-0">
          <Link
            href={`/dashboard/documents/${row.original.document_id}`}
            className="truncate text-sm font-medium text-primary underline-offset-4 hover:underline"
          >
            {row.original.title}
          </Link>
          <p className="truncate text-xs text-muted-foreground">{row.original.original_filename}</p>
        </div>
      </div>
    ),
    enableSorting: true,
    enableHiding: false,
  },
  {
    id: "category",
    accessorKey: "category",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Category" />,
    cell: ({ row }) => getDocumentCategoryLabel(row.original.category),
    enableSorting: true,
  },
  {
    id: "file_type",
    header: "File Type",
    cell: ({ row }) => row.original.extension.toUpperCase(),
    enableSorting: false,
  },
  {
    id: "uploaded_by",
    accessorKey: "uploaded_by_name",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Uploaded By" />,
    enableSorting: false,
  },
  {
    id: "uploaded_at",
    accessorKey: "uploaded_at",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Upload Date" />,
    cell: ({ row }) => formatDate(row.original.uploaded_at),
    enableSorting: true,
  },
  {
    id: "file_size",
    accessorKey: "file_size_bytes",
    header: ({ column }) => <DataTableColumnHeader column={column} title="File Size" />,
    cell: ({ row }) => formatFileSize(row.original.file_size_bytes),
    enableSorting: true,
  },
  {
    id: "status",
    accessorKey: "status",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Status" />,
    cell: ({ row }) => <DocumentStatusBadge status={row.original.status} />,
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
            aria-label={`Actions for ${row.original.title}`}
          >
            <MoreHorizontal className="size-4" aria-hidden="true" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem asChild>
            <Link href={`/dashboard/documents/${row.original.document_id}`}>View details</Link>
          </DropdownMenuItem>
          {isDocumentEditable(row.original.status) && (
            <DropdownMenuItem asChild>
              <Link href={`/dashboard/documents/${row.original.document_id}/edit`}>
                Edit document
              </Link>
            </DropdownMenuItem>
          )}
          <DropdownMenuItem onSelect={() => showSimulatedDownloadToast(row.original)}>
            <Download className="size-4" />
            Download
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    ),
    enableSorting: false,
    enableHiding: false,
  },
];
