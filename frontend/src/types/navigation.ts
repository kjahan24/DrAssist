import type { LucideIcon } from "lucide-react";

export interface NavItem {
  title: string;
  href: string;
  icon: LucideIcon;
  // Permission code required to see this item. Left undefined for every
  // item in this foundation phase — RBAC permission codes aren't seeded
  // yet (see `docs/backend-architecture` Authentication module scope
  // notes), so hardcoding guessed strings here would be worse than no
  // gating at all. `hasPermission()` in `lib/auth/permissions.ts` is
  // already wired and ready the moment real codes exist.
  permission?: string;
  badge?: string;
}

export interface NavGroup {
  title: string;
  items: NavItem[];
}
