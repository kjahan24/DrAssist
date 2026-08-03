import { Badge } from "@/components/ui/badge";
import {
  isNotificationRead,
  isNotificationUnread,
  type NotificationStatus,
} from "@/lib/mock/notifications";

// Folds the real 7-state delivery lifecycle (`pending/scheduled/sent/
// delivered/read/cancelled/expired`) down to the vocabulary this task's
// "Read / Unread status" display field actually asks for, while still
// surfacing the pre-delivery and terminal states distinctly rather than
// hiding them.
const STATUS_LABEL: Record<NotificationStatus, string> = {
  pending: "Pending",
  scheduled: "Scheduled",
  sent: "Unread",
  delivered: "Unread",
  read: "Read",
  cancelled: "Cancelled",
  expired: "Expired",
};

export function NotificationStatusBadge({ status }: { status: NotificationStatus }) {
  if (isNotificationUnread(status)) {
    return <Badge>{STATUS_LABEL[status]}</Badge>;
  }
  if (isNotificationRead(status)) {
    return <Badge variant="secondary">{STATUS_LABEL[status]}</Badge>;
  }
  return <Badge variant="outline">{STATUS_LABEL[status]}</Badge>;
}
