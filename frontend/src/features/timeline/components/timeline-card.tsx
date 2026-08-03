import { Clock, User } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  getTimelineEventColorClass,
  getTimelineEventIcon,
} from "@/features/timeline/lib/event-visuals";
import { formatDateTime } from "@/lib/format";
import type { HealthTimelineEvent } from "@/lib/mock/timeline";
import { cn } from "@/lib/utils";

interface TimelineCardProps {
  event: HealthTimelineEvent;
  compact?: boolean;
  onViewDetails: (event: HealthTimelineEvent) => void;
}

// The content card for one timeline event — Timeline View's `TimelineEvent`
// wraps this with an icon-in-circle + connector line; Compact View
// renders it directly in a dense single-row form (`compact`), with its
// own smaller inline icon since there's no external wrapper to supply
// one.
export function TimelineCard({ event, compact = false, onViewDetails }: TimelineCardProps) {
  const Icon = getTimelineEventIcon(event.event_type);

  if (compact) {
    return (
      <div className="flex items-center gap-3 rounded-md border p-3">
        <div
          className={cn(
            "flex size-8 shrink-0 items-center justify-center rounded-full",
            getTimelineEventColorClass(event.event_type),
          )}
          aria-hidden="true"
        >
          <Icon className="size-4" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="truncate text-sm font-medium">{event.title}</p>
            {event.status_label && (
              <Badge variant="outline" className="shrink-0">
                {event.status_label}
              </Badge>
            )}
          </div>
          <p className="truncate text-xs text-muted-foreground">
            {formatDateTime(event.occurred_at)}
            {event.doctor_name ? ` · ${event.doctor_name}` : ""}
          </p>
        </div>
        <Button variant="ghost" size="sm" className="shrink-0" onClick={() => onViewDetails(event)}>
          Details
        </Button>
      </div>
    );
  }

  return (
    <Card>
      <CardContent className="space-y-3 pt-6">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <p className="text-sm font-semibold">{event.title}</p>
            <p className="mt-0.5 flex items-center gap-1 text-xs text-muted-foreground">
              <Clock className="size-3" aria-hidden="true" />
              {formatDateTime(event.occurred_at)}
            </p>
          </div>
          {event.status_label && <Badge variant="outline">{event.status_label}</Badge>}
        </div>

        {event.doctor_name && (
          <p className="text-sm text-muted-foreground">
            <span className="text-foreground">Doctor:</span> {event.doctor_name}
          </p>
        )}

        {event.summary && <p className="text-sm">{event.summary}</p>}

        <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
          <Link
            href={`/dashboard/patients/${event.patient_id}`}
            className="flex items-center gap-1.5 rounded-sm text-xs text-muted-foreground underline-offset-4 hover:text-foreground hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <User className="size-3.5" aria-hidden="true" />
            {event.patient_name}
          </Link>
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={() => onViewDetails(event)}>
              Details
            </Button>
            <Button variant="outline" size="sm" asChild>
              <Link href={event.quick_action.href}>{event.quick_action.label}</Link>
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
