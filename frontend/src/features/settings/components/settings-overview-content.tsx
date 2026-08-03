import { Bell, KeyRound, SlidersHorizontal, UserRound } from "lucide-react";
import Link from "next/link";
import type { LucideIcon } from "lucide-react";

import { PageHeader } from "@/components/dashboard/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface SettingsOverviewLink {
  title: string;
  description: string;
  href: string;
  icon: LucideIcon;
}

const OVERVIEW_LINKS: SettingsOverviewLink[] = [
  {
    title: "Profile",
    description: "Your professional profile, specialization, and biography.",
    href: "/dashboard/profile",
    icon: UserRound,
  },
  {
    title: "Account",
    description: "Personal information, contact details, language, and time zone.",
    href: "/dashboard/settings/account",
    icon: SlidersHorizontal,
  },
  {
    title: "Security",
    description: "Password, two-factor authentication, and active sessions.",
    href: "/dashboard/settings/security",
    icon: KeyRound,
  },
  {
    title: "Preferences",
    description: "Theme, date/time formats, dashboard layout, and notifications.",
    href: "/dashboard/settings/preferences",
    icon: Bell,
  },
];

// `/dashboard/settings`'s landing page — a hub linking into the other
// settings pages (plus Profile), satisfying this task's own "Navigation
// between settings pages" requirement from a single starting point.
export function SettingsOverviewContent() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        description="Manage your profile, account, security, and preferences."
      />

      <div className="grid gap-4 sm:grid-cols-2">
        {OVERVIEW_LINKS.map((link) => (
          <Card key={link.href}>
            <CardContent className="flex flex-col gap-3 pt-6">
              <div className="flex size-9 items-center justify-center rounded-full bg-muted">
                <link.icon className="size-4 text-muted-foreground" aria-hidden="true" />
              </div>
              <div>
                <p className="text-sm font-medium">{link.title}</p>
                <p className="text-sm text-muted-foreground">{link.description}</p>
              </div>
              <Button variant="outline" size="sm" className="w-fit" asChild>
                <Link href={link.href}>Manage {link.title}</Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
