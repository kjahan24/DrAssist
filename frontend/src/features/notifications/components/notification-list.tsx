import { NotificationCard } from "@/features/notifications/components/notification-card";
import { groupNotificationsByDate, type NotificationItem } from "@/lib/mock/notifications";
import { formatDate } from "@/lib/format";

// Groups already-fetched notifications by date and renders one
// `NotificationCard` per item — the "Group by date" feature this task
// asks for, same grouping pattern `TimelineView` already established.
export function NotificationList({ notifications }: { notifications: NotificationItem[] }) {
  const groups = groupNotificationsByDate(notifications);

  return (
    <div className="space-y-6">
      {groups.map((group) => (
        <section
          key={group.dateKey}
          aria-labelledby={`notif-date-${group.dateKey}`}
          className="space-y-3"
        >
          <h3 id={`notif-date-${group.dateKey}`} className="text-sm font-semibold text-foreground">
            {formatDate(group.dateKey, "EEEE, MMMM d, yyyy")}
          </h3>
          <div className="space-y-2">
            {group.notifications.map((notification) => (
              <NotificationCard key={notification.notification_id} notification={notification} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
