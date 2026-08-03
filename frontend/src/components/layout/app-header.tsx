import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { UserNav } from "@/components/layout/user-nav";
import { OrgSwitcher } from "@/components/dashboard/org-switcher";
import { NotificationBell } from "@/components/shared/notifications/notification-bell";
import { CommandPaletteTrigger } from "@/features/command-palette/components/command-palette-trigger";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";

export function AppHeader() {
  return (
    <header className="sticky top-0 z-10 flex h-14 shrink-0 items-center gap-2 border-b bg-background/80 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <SidebarTrigger className="-ml-1" />
      <Separator orientation="vertical" className="mr-2 h-4" />
      <Breadcrumbs />
      <div className="ml-auto flex items-center gap-2">
        <CommandPaletteTrigger />
        <OrgSwitcher />
        <NotificationBell />
        <ThemeToggle />
        <UserNav />
      </div>
    </header>
  );
}
