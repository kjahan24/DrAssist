import { Badge } from "@/components/ui/badge";
import { getNotificationPriorityLabel, type NotificationPriority } from "@/lib/mock/notifications";

const PRIORITY_VARIANT: Record<
  NotificationPriority,
  "default" | "outline" | "secondary" | "destructive"
> = {
  low: "secondary",
  normal: "outline",
  high: "default",
  critical: "destructive",
};

export function NotificationPriorityBadge({ priority }: { priority: NotificationPriority }) {
  return (
    <Badge variant={PRIORITY_VARIANT[priority]}>{getNotificationPriorityLabel(priority)}</Badge>
  );
}
