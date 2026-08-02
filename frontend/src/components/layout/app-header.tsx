import { Search } from "lucide-react";

import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { UserNav } from "@/components/layout/user-nav";
import { OrgSwitcher } from "@/components/dashboard/org-switcher";
import { NotificationBell } from "@/components/shared/notifications/notification-bell";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";

export function AppHeader() {
  return (
    <header className="sticky top-0 z-10 flex h-14 shrink-0 items-center gap-2 border-b bg-background/80 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <SidebarTrigger className="-ml-1" />
      <Separator orientation="vertical" className="mr-2 h-4" />
      <Breadcrumbs />
      <div className="ml-auto flex items-center gap-2">
        <div className="relative hidden md:block">
          <Search
            className="absolute left-2.5 top-2.5 size-4 text-muted-foreground"
            aria-hidden="true"
          />
          {/* Not wired up yet — no search endpoint exists for any module
              yet, so this is disabled rather than pretending to work. */}
          <Input
            placeholder="Search..."
            className="w-56 pl-8 lg:w-72"
            disabled
            aria-label="Search (coming soon)"
          />
        </div>
        <OrgSwitcher />
        <NotificationBell />
        <ThemeToggle />
        <UserNav />
      </div>
    </header>
  );
}
