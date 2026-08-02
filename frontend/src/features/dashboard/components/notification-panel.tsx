import { Bell, CalendarClock, FileCheck2, FileUp, Info, type LucideIcon } from "lucide-react";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { formatRelativeTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { DashboardNotification, NotificationType } from "@/lib/mock/doctor-dashboard";

const NOTIFICATION_ICON: Record<NotificationType, LucideIcon> = {
  lab_result: FileCheck2,
  appointment_reminder: CalendarClock,
  document_uploaded: FileUp,
  system: Info,
};

interface NotificationPanelProps {
  notifications: DashboardNotification[];
  isLoading?: boolean;
}

export function NotificationPanel({ notifications, isLoading }: NotificationPanelProps) {
  return (
    <SectionCard title="Notifications" description="Recent alerts and updates.">
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-12 w-full" />
          ))}
        </div>
      ) : notifications.length === 0 ? (
        <EmptyState icon={Bell} title="No notifications" description="You're all caught up." />
      ) : (
        <ul className="space-y-1">
          {notifications.map((notification) => {
            const Icon = NOTIFICATION_ICON[notification.type];
            return (
              <li
                key={notification.notification_id}
                className={cn("flex gap-3 rounded-lg p-2", !notification.read && "bg-accent/50")}
              >
                <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                <div className="min-w-0 flex-1 space-y-0.5">
                  <p className="text-sm font-medium">{notification.title}</p>
                  <p className="truncate text-xs text-muted-foreground">{notification.message}</p>
                  <p className="text-xs text-muted-foreground">
                    {formatRelativeTime(notification.timestamp)}
                  </p>
                </div>
                {!notification.read && (
                  <span
                    className="mt-1.5 size-2 shrink-0 rounded-full bg-primary"
                    role="status"
                    aria-label="Unread"
                  />
                )}
              </li>
            );
          })}
        </ul>
      )}
    </SectionCard>
  );
}
