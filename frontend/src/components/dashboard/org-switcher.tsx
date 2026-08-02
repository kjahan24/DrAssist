"use client";

import { Building2, ChevronsUpDown } from "lucide-react";

import { EmptyState } from "@/components/shared/states/empty-state";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/hooks/use-auth";

// Structural placeholder — same honest pattern as `NotificationBell`
// (`components/shared/notifications/notification-bell.tsx`): the backend
// has no endpoint to list a user's organizations yet, so this never
// claims to show a real organization name, only that an authenticated
// session exists.
export function OrgSwitcher() {
  const { principal } = useAuth();

  if (!principal) return null;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" className="gap-2 px-2">
          <Building2 className="size-4 text-muted-foreground" aria-hidden="true" />
          <span className="hidden max-w-32 truncate text-sm font-medium sm:inline">
            My Organization
          </span>
          <ChevronsUpDown className="size-3.5 text-muted-foreground" aria-hidden="true" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-64">
        <DropdownMenuLabel>Organization</DropdownMenuLabel>
        <div className="p-2">
          <EmptyState
            icon={Building2}
            title="Switching coming soon"
            description="Multi-organization support isn't available yet."
          />
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
