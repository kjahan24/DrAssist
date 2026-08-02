import Link from "next/link";
import { FilePlus2, FileX2 } from "lucide-react";

import { EmptyState } from "@/components/shared/states/empty-state";
import { Button } from "@/components/ui/button";

interface SoapNoteEmptyStateProps {
  variant: "empty" | "no-results";
}

// Two distinct messages, matching two distinct realities: "no SOAP notes
// exist at all yet" (has a CTA) vs. "notes exist, your search/filters
// just don't match any" (doesn't).
export function SoapNoteEmptyState({ variant }: SoapNoteEmptyStateProps) {
  if (variant === "no-results") {
    return (
      <EmptyState
        icon={FileX2}
        title="No SOAP notes match your search"
        description="Try adjusting your search or filters."
      />
    );
  }

  return (
    <EmptyState
      icon={FileX2}
      title="No SOAP notes yet"
      description="Get started by documenting your first SOAP note."
      action={
        <Button asChild size="sm">
          <Link href="/dashboard/soap-notes/new">
            <FilePlus2 className="size-4" />
            New SOAP Note
          </Link>
        </Button>
      }
    />
  );
}
