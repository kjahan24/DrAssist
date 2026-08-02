import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
  // Defaults to a plain paragraph, correct for every existing usage
  // (dashboard placeholders, inline table/notification empty states,
  // where a surrounding page already has its own h1). Pages where this
  // *is* the page's only heading (Blog/Careers placeholders, the global
  // 404) pass "h1" instead.
  titleAs?: "h1" | "p";
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
  titleAs: TitleTag = "p",
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed p-12 text-center",
        className,
      )}
    >
      {Icon && (
        <div className="flex size-12 items-center justify-center rounded-full bg-muted">
          <Icon className="size-6 text-muted-foreground" />
        </div>
      )}
      <div className="space-y-1">
        <TitleTag className="text-sm font-medium">{title}</TitleTag>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      {action}
    </div>
  );
}
