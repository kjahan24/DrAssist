import Link from "next/link";
import { UserPlus, UsersRound } from "lucide-react";

import { EmptyState } from "@/components/shared/states/empty-state";
import { Button } from "@/components/ui/button";

interface FamilyEmptyStateProps {
  variant: "empty" | "no-results";
}

// Two distinct messages, matching two distinct realities: "no family
// members have ever been invited" (has a CTA) vs. "members exist, your
// search/filters just don't match any" (doesn't) — same reasoning every
// other module's empty state already applies.
export function FamilyEmptyState({ variant }: FamilyEmptyStateProps) {
  if (variant === "no-results") {
    return (
      <EmptyState
        icon={UsersRound}
        title="No family members match your search"
        description="Try adjusting your search or filters."
      />
    );
  }

  return (
    <EmptyState
      icon={UsersRound}
      title="No family members yet"
      description="Invite a trusted family member or caregiver to share access."
      action={
        <Button asChild size="sm">
          <Link href="/dashboard/family/invitations/new">
            <UserPlus className="size-4" />
            Invite Family Member
          </Link>
        </Button>
      }
    />
  );
}
