import type { Metadata } from "next";

import { ProfileContent } from "@/features/settings/components/profile-content";
import { SettingsSidebar } from "@/features/settings/components/settings-sidebar";

export const metadata: Metadata = { title: "Profile" };

// `/dashboard/profile` lives outside `app/(dashboard)/dashboard/settings/`,
// so it isn't covered by that segment's shared layout — `SettingsSidebar`
// is rendered here directly instead, so all five pages in this module
// (Profile, Settings Overview, Account, Security, Preferences)
// cross-navigate consistently. See `SettingsSidebar`'s own docstring.
export default function ProfilePage() {
  return (
    <div className="flex flex-col gap-6 lg:flex-row">
      <SettingsSidebar />
      <div className="min-w-0 flex-1">
        <ProfileContent />
      </div>
    </div>
  );
}
