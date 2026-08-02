import Link from "next/link";
import { ClipboardPlus, ClipboardX } from "lucide-react";

import { EmptyState } from "@/components/shared/states/empty-state";
import { Button } from "@/components/ui/button";

interface VisitEmptyStateProps {
  variant: "empty" | "no-results";
}

// Two distinct messages, matching two distinct realities: "no visits
// exist at all yet" (has a CTA) vs. "visits exist, your search/filters
// just don't match any" (doesn't).
export function VisitEmptyState({ variant }: VisitEmptyStateProps) {
  if (variant === "no-results") {
    return (
      <EmptyState
        icon={ClipboardX}
        title="No visits match your search"
        description="Try adjusting your search or filters."
      />
    );
  }

  return (
    <EmptyState
      icon={ClipboardX}
      title="No visits yet"
      description="Get started by recording your first patient visit."
      action={
        <Button asChild size="sm">
          <Link href="/dashboard/visits/new">
            <ClipboardPlus className="size-4" />
            New Visit
          </Link>
        </Button>
      }
    />
  );
}
