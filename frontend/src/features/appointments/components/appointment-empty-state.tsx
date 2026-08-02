import Link from "next/link";
import { CalendarPlus, CalendarX2 } from "lucide-react";

import { EmptyState } from "@/components/shared/states/empty-state";
import { Button } from "@/components/ui/button";

interface AppointmentEmptyStateProps {
  variant: "empty" | "no-results";
}

// Two distinct messages, matching two distinct realities: "no
// appointments exist at all yet" (has a CTA) vs. "appointments exist,
// your search/filters just don't match any" (doesn't).
export function AppointmentEmptyState({ variant }: AppointmentEmptyStateProps) {
  if (variant === "no-results") {
    return (
      <EmptyState
        icon={CalendarX2}
        title="No appointments match your search"
        description="Try adjusting your search or filters."
      />
    );
  }

  return (
    <EmptyState
      icon={CalendarX2}
      title="No appointments yet"
      description="Get started by scheduling your first appointment."
      action={
        <Button asChild size="sm">
          <Link href="/dashboard/appointments/new">
            <CalendarPlus className="size-4" />
            New Appointment
          </Link>
        </Button>
      }
    />
  );
}
