import type { ReactNode } from "react";

import { SettingsSidebar } from "@/features/settings/components/settings-sidebar";

// Shared by every page under `/dashboard/settings/*` (Overview, Account,
// Security, Preferences) — `/dashboard/profile` lives at a different URL
// segment so it isn't covered by this layout automatically, but its own
// composer renders `SettingsSidebar` directly too, so all five pages in
// this module cross-navigate consistently.
export default function SettingsLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-col gap-6 lg:flex-row">
      <SettingsSidebar />
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
