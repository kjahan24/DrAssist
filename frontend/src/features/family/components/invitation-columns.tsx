"use client";

import type { ColumnDef } from "@tanstack/react-table";
import Link from "next/link";

import { DataTableColumnHeader } from "@/components/shared/data-table/data-table-column-header";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { FamilyInvitationStatusBadge } from "@/features/family/components/family-invitation-status-badge";
import { InvitationRowActions } from "@/features/family/components/invitation-row-actions";
import { formatDate } from "@/lib/format";
import {
  getAccessLevelLabel,
  getRelationshipLabel,
  type FamilyMember,
} from "@/lib/mock/family-members";
import { getInitials } from "@/lib/utils";

export const invitationColumns: ColumnDef<FamilyMember>[] = [
  {
    id: "recipient",
    accessorKey: "member_name",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Recipient" />,
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
          <p className="truncate text-xs text-muted-foreground">{row.original.email}</p>
        </div>
      </Link>
    ),
    enableSorting: true,
    enableHiding: false,
  },
  {
    id: "patient",
    header: "Patient",
    cell: ({ row }) => (
      <Link
        href={`/dashboard/patients/${row.original.patient_id}`}
        className="text-primary underline-offset-4 hover:underline"
      >
        {row.original.patient_name}
      </Link>
    ),
    enableSorting: false,
  },
  {
    id: "relationship",
    accessorKey: "relationship",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Relationship" />,
    cell: ({ row }) => getRelationshipLabel(row.original.relationship),
    enableSorting: true,
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
    header: ({ column }) => <DataTableColumnHeader column={column} title="Sent Date" />,
    cell: ({ row }) => formatDate(row.original.invited_at),
    enableSorting: true,
  },
  {
    id: "expires",
    header: "Expires",
    cell: ({ row }) =>
      row.original.status === "pending" ? (
        formatDate(row.original.invitation_expires_at)
      ) : (
        <span className="text-muted-foreground">—</span>
      ),
    enableSorting: false,
  },
  {
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => <InvitationRowActions member={row.original} />,
    enableSorting: false,
    enableHiding: false,
  },
];
