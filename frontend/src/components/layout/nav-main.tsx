"use client";

import { SidebarSection } from "@/components/dashboard/sidebar-section";
import { navigation } from "@/config/navigation";
import { useAuth } from "@/hooks/use-auth";
import type { NavGroup } from "@/types/navigation";

export function NavMain() {
  const { can } = useAuth();

  const visibleGroups: NavGroup[] = navigation.map((group) => ({
    ...group,
    items: group.items.filter((item) => !item.permission || can(item.permission)),
  }));

  return (
    <>
      {visibleGroups.map((group) => (
        <SidebarSection key={group.title} group={group} />
      ))}
    </>
  );
}
