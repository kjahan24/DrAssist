import Link from "next/link";
import { UserPlus, Users } from "lucide-react";

import { EmptyState } from "@/components/shared/states/empty-state";
import { Button } from "@/components/ui/button";

interface PatientEmptyStateProps {
  variant: "empty" | "no-results";
}

// Two distinct messages, matching two distinct realities: "no patients
// exist at all yet" (has a CTA) vs. "patients exist, your search/filters
// just don't match any" (doesn't — the fix there is adjusting the
// search, not adding data).
export function PatientEmptyState({ variant }: PatientEmptyStateProps) {
  if (variant === "no-results") {
    return (
      <EmptyState
        icon={Users}
        title="No patients match your search"
        description="Try adjusting your search or filters."
      />
    );
  }

  return (
    <EmptyState
      icon={Users}
      title="No patients yet"
      description="Get started by adding your first patient."
      action={
        <Button asChild size="sm">
          <Link href="/dashboard/patients/new">
            <UserPlus className="size-4" />
            Add Patient
          </Link>
        </Button>
      }
    />
  );
}
