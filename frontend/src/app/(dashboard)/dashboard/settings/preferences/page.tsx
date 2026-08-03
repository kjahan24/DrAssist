import type { Metadata } from "next";

import { PreferencesContent } from "@/features/settings/components/preferences-content";

export const metadata: Metadata = { title: "Preferences" };

export default function PreferencesPage() {
  return <PreferencesContent />;
}
