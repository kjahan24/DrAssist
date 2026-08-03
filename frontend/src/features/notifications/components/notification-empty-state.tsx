import { BellOff } from "lucide-react";

import { EmptyState } from "@/components/shared/states/empty-state";

interface NotificationEmptyStateProps {
  variant: "empty" | "no-results";
}

// Two distinct messages, matching two distinct realities: "you have no
// notifications at all" vs. "notifications exist, your search/filters
// just don't match any" — same reasoning every other module's empty
// state already applies.
export function NotificationEmptyState({ variant }: NotificationEmptyStateProps) {
  if (variant === "no-results") {
    return (
      <EmptyState
        icon={BellOff}
        title="No notifications match your search"
        description="Try adjusting your search or filters."
      />
    );
  }

  return (
    <EmptyState
      icon={BellOff}
      title="You're all caught up"
      description="You have no notifications right now."
    />
  );
}
