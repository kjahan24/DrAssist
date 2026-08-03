import { TimelineDateGroup } from "@/features/timeline/components/timeline-date-group";
import { groupEventsByDate, type HealthTimelineEvent } from "@/lib/mock/timeline";

interface TimelineViewProps {
  events: HealthTimelineEvent[];
  compact: boolean;
  onViewDetails: (event: HealthTimelineEvent) => void;
}

// The top-level renderer for both "views" this module offers: Timeline
// View (the default — full cards linked by a connector line) and
// Compact View (dense single-line rows), toggled via the `compact` flag
// set by `TimelineListContent`. "Filtered View" from the task's own
// Views list isn't a third rendering mode — it's what either view shows
// once `TimelineFilters`/`TimelineSearch` narrow the event list handed
// in here, which is why there's no separate `filtered` prop.
export function TimelineView({ events, compact, onViewDetails }: TimelineViewProps) {
  const groups = groupEventsByDate(events);

  return (
    <div className="space-y-6">
      {groups.map((group) => (
        <TimelineDateGroup
          key={group.dateKey}
          group={group}
          compact={compact}
          onViewDetails={onViewDetails}
        />
      ))}
    </div>
  );
}
