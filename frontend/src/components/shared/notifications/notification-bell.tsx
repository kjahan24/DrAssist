"use client";

import { Bell } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { EmptyState } from "@/components/shared/states/empty-state";

interface NotificationBellProps {
  unreadCount?: number;
}

// Presentational shell for the Notification module (`/notifications` in
// `config/navigation.ts`) — not wired to the backend yet (no business
// modules this phase), so it always renders the empty state. `unreadCount`
// is prop-driven so a future data-fetching hook only needs to pass a
// number in, not touch this component.
export function NotificationBell({ unreadCount = 0 }: NotificationBellProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative" aria-label="Notifications">
          <Bell className="size-5" />
          {unreadCount > 0 && (
            <span className="absolute right-1 top-1 flex size-4 items-center justify-center rounded-full bg-destructive text-[10px] text-destructive-foreground">
              {unreadCount > 9 ? "9+" : unreadCount}
            </span>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel>Notifications</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <div className="p-2">
          <EmptyState title="No notifications" description="You're all caught up." />
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
