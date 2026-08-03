"use client";

import { toast } from "sonner";

import { PageHeader } from "@/components/dashboard/page-header";
import { PageSkeleton } from "@/components/dashboard/page-skeleton";
import { AccountSettingsForm } from "@/features/settings/components/account-settings-form";
import {
  useAccountSettings,
  useUpdateAccountSettings,
} from "@/features/settings/hooks/use-account-settings";
import type { AccountSettings } from "@/lib/mock/settings";

export function AccountSettingsContent() {
  const { data: settings, isLoading } = useAccountSettings();
  const updateSettings = useUpdateAccountSettings();

  if (isLoading || !settings) {
    return <PageSkeleton title="Account" />;
  }

  function handleSubmit(values: AccountSettings) {
    updateSettings.mutate(values, {
      onSuccess: () => toast.success("Account settings saved."),
    });
  }

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader title="Account" description="Manage your personal and contact information." />
      <AccountSettingsForm
        defaultValues={settings}
        onSubmit={handleSubmit}
        isSubmitting={updateSettings.isPending}
      />
    </div>
  );
}
