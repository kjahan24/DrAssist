import type { Metadata } from "next";

import { NotificationSettingsContent } from "@/features/notifications/components/notification-settings-content";

export const metadata: Metadata = { title: "Notification Settings" };

export default function NotificationSettingsPage() {
  return <NotificationSettingsContent />;
}
