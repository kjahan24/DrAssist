"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { Mail } from "lucide-react";

import { DataTableColumnHeader } from "@/components/shared/data-table/data-table-column-header";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { OrganizationStatusBadge } from "@/features/organization/components/organization-status-badge";
import { formatRelativeTime } from "@/lib/format";
import { getMemberStatusLabel, type Member } from "@/lib/mock/members";

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((part) => part[0] ?? "")
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

const STATUS_TO_GENERIC: Record<Member["status"], "active" | "inactive"> = {
  active: "active",
  invited: "inactive",
  suspended: "inactive",
  deactivated: "inactive",
};

export const memberColumns: ColumnDef<Member>[] = [
  {
    id: "name",
    accessorKey: "full_name",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Name" />,
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <Avatar className="size-9">
          <AvatarFallback>{getInitials(row.original.full_name)}</AvatarFallback>
        </Avatar>
        <span className="text-sm font-medium">{row.original.full_name}</span>
      </div>
    ),
    enableSorting: true,
    enableHiding: false,
  },
  {
    id: "role_name",
    accessorKey: "role_name",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Role" />,
    enableSorting: true,
  },
  {
    id: "department_name",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Department" />,
    cell: ({ row }) =>
      row.original.department_name ?? <span className="text-muted-foreground">—</span>,
    enableSorting: true,
  },
  {
    id: "email",
    header: "Email",
    cell: ({ row }) => <span className="text-sm">{row.original.email}</span>,
    enableSorting: false,
  },
  {
    id: "status",
    accessorKey: "status",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Status" />,
    cell: ({ row }) => (
      <OrganizationStatusBadge
        status={STATUS_TO_GENERIC[row.original.status]}
        label={getMemberStatusLabel(row.original.status)}
      />
    ),
    enableSorting: true,
  },
  {
    id: "last_active_at",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Last Active" />,
    cell: ({ row }) =>
      row.original.last_active_at ? (
        formatRelativeTime(row.original.last_active_at)
      ) : (
        <span className="text-muted-foreground">Never</span>
      ),
    enableSorting: true,
  },
  {
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => (
      <Button variant="ghost" size="icon" className="size-8" asChild>
        <a href={`mailto:${row.original.email}`} aria-label={`Email ${row.original.full_name}`}>
          <Mail className="size-4" aria-hidden="true" />
        </a>
      </Button>
    ),
    enableSorting: false,
    enableHiding: false,
  },
];
