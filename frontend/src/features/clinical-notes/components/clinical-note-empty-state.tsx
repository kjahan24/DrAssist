import Link from "next/link";
import { FileX2, NotebookPen } from "lucide-react";

import { EmptyState } from "@/components/shared/states/empty-state";
import { Button } from "@/components/ui/button";

interface ClinicalNoteEmptyStateProps {
  variant: "empty" | "no-results";
}

// Two distinct messages, matching two distinct realities: "no clinical
// notes exist at all yet" (has a CTA) vs. "notes exist, your
// search/filters just don't match any" (doesn't).
export function ClinicalNoteEmptyState({ variant }: ClinicalNoteEmptyStateProps) {
  if (variant === "no-results") {
    return (
      <EmptyState
        icon={FileX2}
        title="No clinical notes match your search"
        description="Try adjusting your search or filters."
      />
    );
  }

  return (
    <EmptyState
      icon={FileX2}
      title="No clinical notes yet"
      description="Get started by documenting your first clinical encounter."
      action={
        <Button asChild size="sm">
          <Link href="/dashboard/clinical-notes/new">
            <NotebookPen className="size-4" />
            New Clinical Note
          </Link>
        </Button>
      }
    />
  );
}
