import type { Metadata } from "next";

import { NotificationListContent } from "@/features/notifications/components/notification-list-content";

export const metadata: Metadata = { title: "Notifications" };

export default function NotificationsPage() {
  return <NotificationListContent />;
}
