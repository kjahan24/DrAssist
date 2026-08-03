import type { LucideIcon } from "lucide-react";

import { EmptyState } from "@/components/shared/states/empty-state";

interface OrganizationEmptyStateProps {
  icon: LucideIcon;
  variant: "empty" | "no-results";
  emptyTitle: string;
  emptyDescription?: string;
  noResultsTitle?: string;
}

// Shared by the Members, Departments, and Locations list pages — same
// "nothing exists yet" vs. "your search/filters just don't match
// anything" distinction every other module's own empty state already
// applies, parameterized instead of duplicated three times.
export function OrganizationEmptyState({
  icon,
  variant,
  emptyTitle,
  emptyDescription,
  noResultsTitle = "No results match your search",
}: OrganizationEmptyStateProps) {
  if (variant === "no-results") {
    return (
      <EmptyState
        icon={icon}
        title={noResultsTitle}
        description="Try adjusting your search or filters."
      />
    );
  }

  return <EmptyState icon={icon} title={emptyTitle} description={emptyDescription} />;
}
