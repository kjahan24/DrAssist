"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight } from "lucide-react";

import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import {
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
} from "@/components/ui/sidebar";
import type { NavItem } from "@/types/navigation";

interface SidebarItemProps {
  item: NavItem;
}

// A leaf item renders as a plain link. An item with `items` renders as a
// collapsible group instead — its own button is a toggle, not a link
// (its `href` is unused), and its children render via shadcn's
// `SidebarMenuSub*` primitives. Recursion stops at one level deep: no
// current item nests more than one level, and the shadcn sidebar's own
// `SidebarMenuSub` styling isn't designed for deeper nesting either.
export function SidebarItem({ item }: SidebarItemProps) {
  const pathname = usePathname();
  const hasChildren = Boolean(item.items?.length);
  const isActive = pathname === item.href;
  const isChildActive = item.items?.some((child) => pathname === child.href) ?? false;

  if (!hasChildren) {
    return (
      <SidebarMenuItem>
        <SidebarMenuButton asChild isActive={isActive} tooltip={item.title}>
          <Link href={item.href}>
            <item.icon />
            <span>{item.title}</span>
          </Link>
        </SidebarMenuButton>
      </SidebarMenuItem>
    );
  }

  return (
    <Collapsible defaultOpen={isChildActive} className="group/collapsible">
      <SidebarMenuItem>
        <CollapsibleTrigger asChild>
          <SidebarMenuButton isActive={isChildActive} tooltip={item.title}>
            <item.icon />
            <span>{item.title}</span>
            <ChevronRight
              className="ml-auto transition-transform duration-200 group-data-[state=open]/collapsible:rotate-90"
              aria-hidden="true"
            />
          </SidebarMenuButton>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <SidebarMenuSub>
            {item.items?.map((child) => (
              <SidebarMenuSubItem key={child.href}>
                <SidebarMenuSubButton asChild isActive={pathname === child.href}>
                  <Link href={child.href}>
                    <span>{child.title}</span>
                  </Link>
                </SidebarMenuSubButton>
              </SidebarMenuSubItem>
            ))}
          </SidebarMenuSub>
        </CollapsibleContent>
      </SidebarMenuItem>
    </Collapsible>
  );
}
