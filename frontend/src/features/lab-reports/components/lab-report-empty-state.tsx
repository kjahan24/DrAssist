import Link from "next/link";
import { FlaskConical, FlaskConicalOff } from "lucide-react";

import { EmptyState } from "@/components/shared/states/empty-state";
import { Button } from "@/components/ui/button";

interface LabReportEmptyStateProps {
  variant: "empty" | "no-results";
}

// Two distinct messages, matching two distinct realities: "no lab
// reports exist at all yet" (has a CTA) vs. "reports exist, your
// search/filters just don't match any" (doesn't).
export function LabReportEmptyState({ variant }: LabReportEmptyStateProps) {
  if (variant === "no-results") {
    return (
      <EmptyState
        icon={FlaskConicalOff}
        title="No lab reports match your search"
        description="Try adjusting your search or filters."
      />
    );
  }

  return (
    <EmptyState
      icon={FlaskConicalOff}
      title="No lab reports yet"
      description="Get started by ordering your first lab report."
      action={
        <Button asChild size="sm">
          <Link href="/dashboard/lab-reports/new">
            <FlaskConical className="size-4" />
            New Lab Report
          </Link>
        </Button>
      }
    />
  );
}
