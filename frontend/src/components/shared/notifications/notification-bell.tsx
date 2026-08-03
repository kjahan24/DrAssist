"use client";

import { Bell } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { EmptyState } from "@/components/shared/states/empty-state";
import { useNotifications } from "@/features/notifications/hooks/use-notifications";
import { formatRelativeTime } from "@/lib/format";

// The "future data-fetching hook" this component's own original
// docstring anticipated (Module 4/Dashboard Shell) — now that the
// Notifications Center module exists, this reads real (mock) unread
// notifications instead of always rendering empty. Self-sufficient
// (calls its own hook) rather than staying purely prop-driven, so the
// one call site in `components/layout/app-header.tsx` needs no changes.
export function NotificationBell() {
  const { data } = useNotifications({
    readStatus: "unread",
    pageSize: 5,
    sortBy: "created_at",
    sortDirection: "desc",
  });
  const items = data?.items ?? [];
  const unreadCount = data?.total ?? 0;

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
        {items.length === 0 ? (
          <div className="p-2">
            <EmptyState title="No notifications" description="You're all caught up." />
          </div>
        ) : (
          <ul className="max-h-80 space-y-1 overflow-y-auto p-1">
            {items.map((notification) => (
              <li key={notification.notification_id}>
                <Link
                  href={notification.quick_action_href ?? "/dashboard/notifications"}
                  className="block rounded-sm px-2 py-2 hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <p className="truncate text-sm font-medium">{notification.title}</p>
                  <p className="truncate text-xs text-muted-foreground">{notification.message}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {formatRelativeTime(notification.created_at)}
                  </p>
                </Link>
              </li>
            ))}
          </ul>
        )}
        <DropdownMenuSeparator />
        <Link
          href="/dashboard/notifications"
          className="block rounded-sm px-2 py-2 text-center text-sm font-medium text-primary hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          View All Notifications
        </Link>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
