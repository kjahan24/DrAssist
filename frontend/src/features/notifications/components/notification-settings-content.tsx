"use client";

import { toast } from "sonner";

import { PageHeader } from "@/components/dashboard/page-header";
import { PageSkeleton } from "@/components/dashboard/page-skeleton";
import { NotificationSettingsForm } from "@/features/notifications/components/notification-settings-form";
import {
  useNotificationPreferences,
  useUpdateNotificationPreferences,
} from "@/features/notifications/hooks/use-notification-preferences";
import type { NotificationPreferences } from "@/lib/mock/notifications";

export function NotificationSettingsContent() {
  const { data: preferences, isLoading } = useNotificationPreferences();
  const updatePreferences = useUpdateNotificationPreferences();

  if (isLoading || !preferences) {
    return <PageSkeleton title="Notification Settings" />;
  }

  function handleSubmit(values: NotificationPreferences) {
    updatePreferences.mutate(values, {
      onSuccess: () => toast.success("Notification settings saved."),
    });
  }

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader
        title="Notification Settings"
        description="Control how and when you receive notifications."
      />
      <NotificationSettingsForm
        defaultValues={preferences}
        onSubmit={handleSubmit}
        isSubmitting={updatePreferences.isPending}
      />
    </div>
  );
}
