import type { ReactNode } from "react";

import { SectionCard } from "@/components/dashboard/section-card";

interface SettingsSectionProps {
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
}

// The standard titled section wrapper used across every Settings/Profile
// page — a thin, module-scoped alias for `SectionCard` (same reasoning
// every other module's own `*DetailsCard` already applies: one
// well-named wrapper per module, even when its body is a pass-through).
export function SettingsSection({ title, description, actions, children }: SettingsSectionProps) {
  return (
    <SectionCard title={title} description={description} actions={actions}>
      {children}
    </SectionCard>
  );
}
