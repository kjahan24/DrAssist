"use client";

import { History, KeyRound, Smartphone } from "lucide-react";
import { toast } from "sonner";

import { PageHeader } from "@/components/dashboard/page-header";
import { Switch } from "@/components/ui/switch";
import { ChangePasswordForm } from "@/features/settings/components/change-password-form";
import { SecurityCard } from "@/features/settings/components/security-card";
import { SessionTable } from "@/features/settings/components/session-table";
import { SettingsSection } from "@/features/settings/components/settings-section";
import {
  useActiveSessions,
  useChangePassword,
  useLoginHistory,
  useRevokeSession,
  useSecurityOverview,
  useSetSessionTrusted,
  useSetTwoFactorEnabled,
  useTrustedDevices,
} from "@/features/settings/hooks/use-security-settings";
import type { ChangePasswordInput } from "@/lib/mock/settings";

export function SecuritySettingsContent() {
  const { data: overview } = useSecurityOverview();
  const setTwoFactorEnabled = useSetTwoFactorEnabled();
  const changePassword = useChangePassword();

  const { data: activeSessions, isLoading: isActiveLoading } = useActiveSessions();
  const { data: loginHistory, isLoading: isHistoryLoading } = useLoginHistory();
  const { data: trustedDevices, isLoading: isTrustedLoading } = useTrustedDevices();
  const revokeSession = useRevokeSession();
  const setSessionTrusted = useSetSessionTrusted();

  function handleChangePassword(values: ChangePasswordInput) {
    changePassword.mutate(values, {
      onSuccess: () => toast.success("Password updated."),
      onError: (error) =>
        toast.error(error instanceof Error ? error.message : "Failed to update password."),
    });
  }

  function handleToggleTwoFactor(enabled: boolean) {
    setTwoFactorEnabled.mutate(enabled, {
      onSuccess: () =>
        toast.success(
          enabled ? "Two-factor authentication enabled." : "Two-factor authentication disabled.",
        ),
    });
  }

  function handleRevoke(sessionId: string) {
    revokeSession.mutate(sessionId, {
      onSuccess: () => toast.success("Session revoked."),
    });
  }

  function handleRemoveTrust(sessionId: string) {
    setSessionTrusted.mutate(
      { sessionId, trusted: false },
      { onSuccess: () => toast.success("Device is no longer trusted.") },
    );
  }

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader title="Security" description="Manage how you sign in and protect your account." />

      <SecurityCard
        icon={KeyRound}
        title="Change Password"
        description="Choose a strong password you don't use elsewhere."
      >
        <ChangePasswordForm
          onSubmit={handleChangePassword}
          isSubmitting={changePassword.isPending}
        />
      </SecurityCard>

      <SecurityCard
        icon={Smartphone}
        title="Two-Factor Authentication"
        description="Require a verification code in addition to your password when signing in."
        action={
          <Switch
            checked={overview?.mfa_enabled ?? false}
            onCheckedChange={handleToggleTwoFactor}
            disabled={!overview || setTwoFactorEnabled.isPending}
            aria-label="Toggle two-factor authentication"
          />
        }
      />

      <SettingsSection
        title="Active Sessions"
        description="Devices currently signed in to your account."
      >
        <SessionTable
          sessions={activeSessions ?? []}
          mode="active"
          isLoading={isActiveLoading}
          onRevoke={handleRevoke}
        />
      </SettingsSection>

      <SettingsSection
        title="Trusted Devices"
        description="Devices you've marked as trusted won't require extra verification."
      >
        <SessionTable
          sessions={trustedDevices ?? []}
          mode="trusted"
          isLoading={isTrustedLoading}
          onToggleTrusted={handleRemoveTrust}
        />
      </SettingsSection>

      <SettingsSection title="Login History" description="A record of sign-ins to your account.">
        <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
          <History className="size-3.5" aria-hidden="true" />
          Showing the most recent sign-ins first.
        </div>
        <SessionTable sessions={loginHistory ?? []} mode="history" isLoading={isHistoryLoading} />
      </SettingsSection>
    </div>
  );
}
