import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { Card, CardContent } from "@/components/ui/card";

interface PreferenceCardProps {
  icon: LucideIcon;
  title: string;
  description: string;
  control: ReactNode;
}

// A titled row for one preference (Theme, Date Format, Dashboard
// Layout, ...) — icon + title + description on the left, the actual
// control (a `ThemeSelector`/`Select`/`Button`) on the right. The
// Preferences-page counterpart to `SecurityCard`.
export function PreferenceCard({ icon: Icon, title, description, control }: PreferenceCardProps) {
  return (
    <Card>
      <CardContent className="flex flex-col gap-4 pt-6 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-muted">
            <Icon className="size-4 text-muted-foreground" aria-hidden="true" />
          </div>
          <div>
            <p className="text-sm font-medium">{title}</p>
            <p className="text-xs text-muted-foreground">{description}</p>
          </div>
        </div>
        <div className="sm:w-48">{control}</div>
      </CardContent>
    </Card>
  );
}
