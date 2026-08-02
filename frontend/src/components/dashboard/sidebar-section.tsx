import { SidebarItem } from "@/components/dashboard/sidebar-item";
import { SidebarGroup, SidebarGroupLabel, SidebarMenu } from "@/components/ui/sidebar";
import type { NavGroup } from "@/types/navigation";

export function SidebarSection({ group }: { group: NavGroup }) {
  return (
    <SidebarGroup>
      <SidebarGroupLabel>{group.title}</SidebarGroupLabel>
      <SidebarMenu>
        {group.items.map((item) => (
          <SidebarItem key={item.href} item={item} />
        ))}
      </SidebarMenu>
    </SidebarGroup>
  );
}
