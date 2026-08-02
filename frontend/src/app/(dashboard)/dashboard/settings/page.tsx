import { PageHeader } from "@/components/dashboard/page-header";
import { SectionCard } from "@/components/dashboard/section-card";
import { ThemeToggle } from "@/components/layout/theme-toggle";

export const metadata = { title: "Settings" };

// The one settings section that's genuinely infrastructure, not a
// business module: appearance. Profile/organization/notification
// preferences etc. belong to their owning modules once those are built.
export default function SettingsPage() {
  return (
    <div className="max-w-2xl space-y-6">
      <PageHeader title="Settings" description="Manage your application preferences." />
      <SectionCard title="Appearance" description="Switch between light, dark, or system theme.">
        <ThemeToggle />
      </SectionCard>
    </div>
  );
}
