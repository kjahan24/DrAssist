import Link from "next/link";
import { Stethoscope } from "lucide-react";

import { NavMain } from "@/components/layout/nav-main";
import { Sidebar, SidebarContent, SidebarHeader, SidebarRail } from "@/components/ui/sidebar";
import { siteConfig } from "@/config/site";

export function AppSidebar() {
  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <Link href="/dashboard" className="flex items-center gap-2 px-2 py-1.5">
          <Stethoscope className="size-6 shrink-0 text-primary" />
          <span className="truncate text-base font-semibold group-data-[collapsible=icon]:hidden">
            {siteConfig.name}
          </span>
        </Link>
      </SidebarHeader>
      <SidebarContent>
        <NavMain />
      </SidebarContent>
      <SidebarRail />
    </Sidebar>
  );
}
