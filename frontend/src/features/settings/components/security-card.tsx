import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { Card, CardContent } from "@/components/ui/card";

interface SecurityCardProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: ReactNode;
  children?: ReactNode;
}

// A titled row for one security feature (Two-Factor Authentication,
// Change Password, ...) — icon + title + description with an optional
// header-row action (a `Switch`/`Button`) and optional expanded content
// below (e.g. `ChangePasswordForm`).
export function SecurityCard({
  icon: Icon,
  title,
  description,
  action,
  children,
}: SecurityCardProps) {
  return (
    <Card>
      <CardContent className="space-y-4 pt-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-muted">
              <Icon className="size-4 text-muted-foreground" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm font-medium">{title}</p>
              <p className="text-xs text-muted-foreground">{description}</p>
            </div>
          </div>
          {action}
        </div>
        {children}
      </CardContent>
    </Card>
  );
}
