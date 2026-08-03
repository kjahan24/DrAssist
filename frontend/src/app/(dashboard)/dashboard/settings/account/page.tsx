import type { Metadata } from "next";

import { AccountSettingsContent } from "@/features/settings/components/account-settings-content";

export const metadata: Metadata = { title: "Account Settings" };

export default function AccountSettingsPage() {
  return <AccountSettingsContent />;
}
