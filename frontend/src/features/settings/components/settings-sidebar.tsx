"use client";

import { Bell, KeyRound, Settings2, SlidersHorizontal, UserRound } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

interface SettingsNavItem {
  title: string;
  href: string;
  icon: typeof Settings2;
}

const SETTINGS_NAV_ITEMS: SettingsNavItem[] = [
  { title: "Overview", href: "/dashboard/settings", icon: Settings2 },
  { title: "Profile", href: "/dashboard/profile", icon: UserRound },
  { title: "Account", href: "/dashboard/settings/account", icon: SlidersHorizontal },
  { title: "Security", href: "/dashboard/settings/security", icon: KeyRound },
  { title: "Preferences", href: "/dashboard/settings/preferences", icon: Bell },
];

// A local sub-navigation scoped to the Settings/Profile pages — distinct
// from the app-wide `Sidebar` (`components/dashboard/sidebar-item.tsx`),
// which is tied to a single global `SidebarProvider` context this
// secondary nav doesn't participate in. Renders as a vertical menu on
// desktop and a horizontal scrollable tab strip on mobile, satisfying
// this task's own "Navigation between settings pages" requirement.
export function SettingsSidebar() {
  const pathname = usePathname();

  return (
    <nav aria-label="Settings" className="shrink-0 lg:w-56">
      <ul className="flex gap-1 overflow-x-auto pb-2 lg:flex-col lg:overflow-visible lg:pb-0">
        {SETTINGS_NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          return (
            <li key={item.href} className="shrink-0 lg:shrink">
              <Link
                href={item.href}
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  "flex items-center gap-2 whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  isActive
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                )}
              >
                <item.icon className="size-4 shrink-0" aria-hidden="true" />
                {item.title}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
