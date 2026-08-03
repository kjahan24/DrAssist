import Link from "next/link";
import { FilePlus2, FileX2 } from "lucide-react";

import { EmptyState } from "@/components/shared/states/empty-state";
import { Button } from "@/components/ui/button";

interface PrescriptionEmptyStateProps {
  variant: "empty" | "no-results";
}

// Two distinct messages, matching two distinct realities: "no
// prescriptions exist at all yet" (has a CTA) vs. "prescriptions exist,
// your search/filters just don't match any" (doesn't).
export function PrescriptionEmptyState({ variant }: PrescriptionEmptyStateProps) {
  if (variant === "no-results") {
    return (
      <EmptyState
        icon={FileX2}
        title="No prescriptions match your search"
        description="Try adjusting your search or filters."
      />
    );
  }

  return (
    <EmptyState
      icon={FileX2}
      title="No prescriptions yet"
      description="Get started by writing your first prescription."
      action={
        <Button asChild size="sm">
          <Link href="/dashboard/prescriptions/new">
            <FilePlus2 className="size-4" />
            New Prescription
          </Link>
        </Button>
      }
    />
  );
}
