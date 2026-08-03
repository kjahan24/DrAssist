import { TimelineCard } from "@/features/timeline/components/timeline-card";
import { TimelineEvent } from "@/features/timeline/components/timeline-event";
import type { HealthTimelineEvent, TimelineDateGroupData } from "@/lib/mock/timeline";
import { formatDate } from "@/lib/format";

interface TimelineDateGroupProps {
  group: TimelineDateGroupData;
  compact: boolean;
  onViewDetails: (event: HealthTimelineEvent) => void;
}

// One day's worth of events under a date heading — the connector line
// inside `TimelineEvent` only runs within a group, so each day reads as
// its own short chain rather than one unbroken line down the whole page.
export function TimelineDateGroup({ group, compact, onViewDetails }: TimelineDateGroupProps) {
  return (
    <section aria-labelledby={`timeline-date-${group.dateKey}`} className="space-y-3">
      <h3
        id={`timeline-date-${group.dateKey}`}
        className="sticky top-0 z-10 -mx-1 bg-background/95 px-1 py-1 text-sm font-semibold text-foreground backdrop-blur supports-[backdrop-filter]:bg-background/80"
      >
        {formatDate(group.dateKey, "EEEE, MMMM d, yyyy")}
      </h3>

      {compact ? (
        <div className="space-y-2">
          {group.events.map((event) => (
            <TimelineCard
              key={event.event_id}
              event={event}
              compact
              onViewDetails={onViewDetails}
            />
          ))}
        </div>
      ) : (
        <ol className="space-y-0">
          {group.events.map((event, index) => (
            <TimelineEvent
              key={event.event_id}
              event={event}
              isLast={index === group.events.length - 1}
              onViewDetails={onViewDetails}
            />
          ))}
        </ol>
      )}
    </section>
  );
}
