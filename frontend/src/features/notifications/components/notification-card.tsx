"use client";

import { Archive, Check, MoreHorizontal, Trash2 } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  useArchiveNotification,
  useDeleteNotification,
  useMarkNotificationAsRead,
  useMarkNotificationAsUnread,
} from "@/features/notifications/hooks/use-notifications";
import {
  getNotificationCategoryColorClass,
  getNotificationCategoryIcon,
} from "@/features/notifications/lib/notification-visuals";
import { NotificationPriorityBadge } from "@/features/notifications/components/notification-priority-badge";
import { NotificationStatusBadge } from "@/features/notifications/components/notification-status-badge";
import { formatRelativeTime } from "@/lib/format";
import {
  getNotificationCategoryLabel,
  isNotificationRead,
  isNotificationUnread,
  type NotificationItem,
} from "@/lib/mock/notifications";
import { cn } from "@/lib/utils";

// The reusable notification row — shown by `NotificationList`, grouped
// under a date heading. Owns its own read/unread/archive/delete actions
// (each backed by a real hook call), so it must be a real component
// (not an inline render function) for the Rules of Hooks to hold.
export function NotificationCard({ notification }: { notification: NotificationItem }) {
  const markAsRead = useMarkNotificationAsRead();
  const markAsUnread = useMarkNotificationAsUnread();
  const archiveNotification = useArchiveNotification();
  const deleteNotification = useDeleteNotification();

  const Icon = getNotificationCategoryIcon(notification.category);
  const unread = isNotificationUnread(notification.status);
  const canToggleRead = unread || isNotificationRead(notification.status);

  function handleToggleRead() {
    if (unread) {
      markAsRead.mutate(notification.notification_id);
    } else {
      markAsUnread.mutate(notification.notification_id);
    }
  }

  function handleArchive() {
    archiveNotification.mutate(notification.notification_id, {
      onSuccess: () => toast.success("Notification archived."),
    });
  }

  function handleDelete() {
    deleteNotification.mutate(notification.notification_id, {
      onSuccess: () => toast.success("Notification deleted."),
    });
  }

  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-lg border p-4 transition-colors",
        unread && "border-primary/30 bg-primary/[0.03]",
      )}
    >
      <div
        className={cn(
          "flex size-9 shrink-0 items-center justify-center rounded-full",
          getNotificationCategoryColorClass(notification.category),
        )}
        aria-hidden="true"
      >
        <Icon className="size-4" />
      </div>

      <div className="min-w-0 flex-1 space-y-1.5">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="flex items-center gap-2 text-sm font-medium">
              {unread && (
                <span className="size-1.5 shrink-0 rounded-full bg-primary" aria-hidden="true" />
              )}
              {notification.title}
            </p>
            <p className="mt-0.5 text-sm text-muted-foreground">{notification.message}</p>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="size-8 shrink-0"
                aria-label={`Actions for ${notification.title}`}
              >
                <MoreHorizontal className="size-4" aria-hidden="true" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {canToggleRead && (
                <DropdownMenuItem onSelect={handleToggleRead}>
                  <Check className="size-4" />
                  {unread ? "Mark as read" : "Mark as unread"}
                </DropdownMenuItem>
              )}
              <DropdownMenuItem onSelect={handleArchive} disabled={notification.is_archived}>
                <Archive className="size-4" />
                Archive
              </DropdownMenuItem>
              <DropdownMenuItem
                onSelect={handleDelete}
                className="text-destructive focus:text-destructive"
              >
                <Trash2 className="size-4" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-muted-foreground">
            {getNotificationCategoryLabel(notification.category)}
          </span>
          <NotificationPriorityBadge priority={notification.priority} />
          <NotificationStatusBadge status={notification.status} />
          <span className="text-xs text-muted-foreground">
            {formatRelativeTime(notification.created_at)}
          </span>
        </div>

        {(notification.reference_label || notification.quick_action_href) && (
          <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
            {notification.reference_label && (
              <span className="text-xs text-muted-foreground">
                Related: {notification.reference_label}
              </span>
            )}
            {notification.quick_action_href && (
              <Button variant="outline" size="sm" asChild>
                <Link href={notification.quick_action_href}>View</Link>
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
