import {
  CalendarDays,
  CalendarPlus,
  FileStack,
  FileText,
  History,
  UserPlus,
  type LucideIcon,
} from "lucide-react";

import { DashboardCard } from "@/components/dashboard/dashboard-card";
import { SectionCard } from "@/components/dashboard/section-card";
import { doctorDashboardQuickActions } from "@/lib/mock/doctor-dashboard";

// Icons are matched to the mock data's `href` here (presentation), same
// pattern as `StatsGrid` — the link definitions themselves come from
// `lib/mock/doctor-dashboard.ts`, not hardcoded in this component.
const ICON_BY_HREF: Record<string, LucideIcon> = {
  "/dashboard/appointments/new": CalendarPlus,
  "/dashboard/patients/new": UserPlus,
  "/dashboard/schedule": CalendarDays,
  "/dashboard/clinical-notes": FileText,
  "/dashboard/documents": FileStack,
  "/dashboard/timeline": History,
};

export function QuickActions() {
  return (
    <SectionCard title="Quick Actions" description="Common tasks, one click away.">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {doctorDashboardQuickActions.map((action) => (
          <DashboardCard
            key={action.href}
            title={action.title}
            description={action.description}
            href={action.href}
            icon={ICON_BY_HREF[action.href] ?? FileText}
          />
        ))}
      </div>
    </SectionCard>
  );
}
