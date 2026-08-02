import Link from "next/link";
import { ArrowRight, type LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface DashboardCardProps {
  title: string;
  description: string;
  href: string;
  icon: LucideIcon;
  badge?: string;
  className?: string;
}

// A single quick-link tile — used on the Dashboard overview page to
// surface where each future business module will live. Purely a link (no
// data, no logic): the same "architecture, not the feature" placeholder
// every sidebar nav item and marketing nav link already is.
export function DashboardCard({
  title,
  description,
  href,
  icon: Icon,
  badge,
  className,
}: DashboardCardProps) {
  return (
    <Link
      href={href}
      className={cn(
        "group rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        className,
      )}
    >
      <Card className="h-full transition-colors group-hover:border-primary/50 group-hover:bg-accent/50">
        <CardContent className="flex items-start gap-4 pt-6">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
            <Icon className="size-5 text-primary" aria-hidden="true" />
          </div>
          <div className="min-w-0 flex-1 space-y-1">
            <div className="flex items-center gap-2">
              <h3 className="font-medium">{title}</h3>
              {badge && (
                <Badge variant="outline" className="text-xs font-normal">
                  {badge}
                </Badge>
              )}
            </div>
            <p className="text-sm text-muted-foreground">{description}</p>
          </div>
          <ArrowRight
            className="size-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5"
            aria-hidden="true"
          />
        </CardContent>
      </Card>
    </Link>
  );
}
