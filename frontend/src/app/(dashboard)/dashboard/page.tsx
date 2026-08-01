import { LayoutDashboard } from "lucide-react";

import { EmptyState } from "@/components/shared/states/empty-state";

export const metadata = { title: "Dashboard" };

// Placeholder overview — deliberately has no stat cards or charts wired to
// real data yet, since no business module's API client exists this phase
// (see this task's own "Do NOT implement business modules yet" scope).
// `components/shared/charts/stat-card.tsx` and friends are ready for a
// future task to drop in here.
export default function DashboardPage() {
  return (
    <div className="flex flex-1 items-center justify-center">
      <EmptyState
        icon={LayoutDashboard}
        title="Welcome to DrAssist"
        description="Module dashboards will appear here as each clinical area is built out."
      />
    </div>
  );
}
