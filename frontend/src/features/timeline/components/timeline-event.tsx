import { TimelineCard } from "@/features/timeline/components/timeline-card";
import {
  getTimelineEventColorClass,
  getTimelineEventIcon,
} from "@/features/timeline/lib/event-visuals";
import type { HealthTimelineEvent } from "@/lib/mock/timeline";
import { cn } from "@/lib/utils";

interface TimelineEventProps {
  event: HealthTimelineEvent;
  isLast: boolean;
  onViewDetails: (event: HealthTimelineEvent) => void;
}

// One "node" in the full Timeline View — the icon-in-circle plus the
// vertical connector line down to the next node, wrapping `TimelineCard`
// for the actual content. Compact View skips this wrapper entirely and
// renders `TimelineCard`s directly (see `TimelineView`).
export function TimelineEvent({ event, isLast, onViewDetails }: TimelineEventProps) {
  const Icon = getTimelineEventIcon(event.event_type);

  return (
    <li className="relative flex gap-4 pb-6 last:pb-0">
      {!isLast && (
        <span
          className="absolute left-[15px] top-8 h-[calc(100%-2rem)] w-px bg-border"
          aria-hidden="true"
        />
      )}
      <div
        className={cn(
          "z-10 flex size-8 shrink-0 items-center justify-center rounded-full ring-4 ring-background",
          getTimelineEventColorClass(event.event_type),
        )}
        aria-hidden="true"
      >
        <Icon className="size-4" />
      </div>
      <div className="min-w-0 flex-1">
        <TimelineCard event={event} onViewDetails={onViewDetails} />
      </div>
    </li>
  );
}
