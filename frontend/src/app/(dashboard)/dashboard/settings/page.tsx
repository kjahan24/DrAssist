import type { Metadata } from "next";

import { SettingsOverviewContent } from "@/features/settings/components/settings-overview-content";

export const metadata: Metadata = { title: "Settings" };

// The old placeholder here was a bare Appearance/`ThemeToggle` card
// (Module 1) with its own docstring noting "Profile/organization/
// notification preferences etc. belong to their owning modules once
// those are built" — that hand-off is this module. Theme now lives in
// `ThemeSelector` on `/dashboard/settings/preferences`; this page is the
// navigational hub linking into Profile/Account/Security/Preferences.
export default function SettingsPage() {
  return <SettingsOverviewContent />;
}
