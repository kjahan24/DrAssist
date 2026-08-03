import type { LucideIcon } from "lucide-react";

import { EmptyState } from "@/components/shared/states/empty-state";

interface SettingsEmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
}

// A module-scoped alias for the shared `EmptyState`, used by
// `SessionTable` when a given session view (Active Sessions/Login
// History/Trusted Devices) has nothing to show.
export function SettingsEmptyState({ icon, title, description }: SettingsEmptyStateProps) {
  return <EmptyState icon={icon} title={title} description={description} />;
}
