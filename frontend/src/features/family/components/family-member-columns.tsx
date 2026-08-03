"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { MoreHorizontal } from "lucide-react";
import Link from "next/link";

import { DataTableColumnHeader } from "@/components/shared/data-table/data-table-column-header";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { FamilyInvitationStatusBadge } from "@/features/family/components/family-invitation-status-badge";
import { formatDate, formatRelativeTime } from "@/lib/format";
import {
  getAccessLevelLabel,
  getRelationshipLabel,
  isFamilyAccessRevocable,
  type FamilyMember,
} from "@/lib/mock/family-members";
import { getInitials } from "@/lib/utils";

export const familyMemberColumns: ColumnDef<FamilyMember>[] = [
  {
    id: "member",
    accessorKey: "member_name",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Member Name" />,
    cell: ({ row }) => (
      <Link
        href={`/dashboard/family/${row.original.family_access_id}`}
        className="flex items-center gap-3 rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <Avatar className="size-9">
          <AvatarFallback>{getInitials(row.original.member_name)}</AvatarFallback>
        </Avatar>
        <div className="min-w-0">
          <p className="truncate text-sm font-medium">{row.original.member_name}</p>
          <p className="truncate text-xs text-muted-foreground">for {row.original.patient_name}</p>
        </div>
      </Link>
    ),
    enableSorting: true,
    enableHiding: false,
  },
  {
    id: "relationship",
    accessorKey: "relationship",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Relationship" />,
    cell: ({ row }) => getRelationshipLabel(row.original.relationship),
    enableSorting: true,
  },
  {
    id: "email",
    header: "Email",
    cell: ({ row }) => <span className="text-sm">{row.original.email}</span>,
    enableSorting: false,
  },
  {
    id: "phone",
    header: "Phone",
    cell: ({ row }) => <span className="text-sm">{row.original.phone}</span>,
    enableSorting: false,
  },
  {
    id: "access_level",
    accessorKey: "access_level",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Access Level" />,
    cell: ({ row }) => (
      <Badge variant="outline">{getAccessLevelLabel(row.original.access_level)}</Badge>
    ),
    enableSorting: true,
  },
  {
    id: "status",
    accessorKey: "status",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Status" />,
    cell: ({ row }) => <FamilyInvitationStatusBadge status={row.original.status} />,
    enableSorting: true,
  },
  {
    id: "invited_at",
    accessorKey: "invited_at",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Invited Date" />,
    cell: ({ row }) => formatDate(row.original.invited_at),
    enableSorting: true,
  },
  {
    id: "last_activity_at",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Last Activity" />,
    cell: ({ row }) =>
      row.original.last_activity_at ? (
        formatRelativeTime(row.original.last_activity_at)
      ) : (
        <span className="text-muted-foreground">—</span>
      ),
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
            aria-label={`Actions for ${row.original.member_name}`}
          >
            <MoreHorizontal className="size-4" aria-hidden="true" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem asChild>
            <Link href={`/dashboard/family/${row.original.family_access_id}`}>View details</Link>
          </DropdownMenuItem>
          {isFamilyAccessRevocable(row.original.status) && (
            <DropdownMenuItem asChild>
              <Link href={`/dashboard/family/${row.original.family_access_id}`}>Revoke access</Link>
            </DropdownMenuItem>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
    ),
    enableSorting: false,
    enableHiding: false,
  },
];
