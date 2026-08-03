import { History } from "lucide-react";

import { EmptyState } from "@/components/shared/states/empty-state";

interface TimelineEmptyStateProps {
  variant: "empty" | "no-results";
}

// Two distinct messages, matching two distinct realities: "this patient
// has no recorded health events at all yet" vs. "events exist, your
// search/filters just don't match any" — same reasoning every other
// module's empty state already applies.
export function TimelineEmptyState({ variant }: TimelineEmptyStateProps) {
  if (variant === "no-results") {
    return (
      <EmptyState
        icon={History}
        title="No timeline events match your search"
        description="Try adjusting your search or filters."
      />
    );
  }

  return (
    <EmptyState
      icon={History}
      title="No health timeline yet"
      description="This patient has no recorded appointments, visits, or clinical events."
    />
  );
}
