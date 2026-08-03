import type { Metadata } from "next";

import { SecuritySettingsContent } from "@/features/settings/components/security-settings-content";

export const metadata: Metadata = { title: "Security Settings" };

export default function SecuritySettingsPage() {
  return <SecuritySettingsContent />;
}
