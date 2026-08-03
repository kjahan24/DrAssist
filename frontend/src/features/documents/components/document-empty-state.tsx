import Link from "next/link";
import { FileX2, Upload } from "lucide-react";

import { EmptyState } from "@/components/shared/states/empty-state";
import { Button } from "@/components/ui/button";

interface DocumentEmptyStateProps {
  variant: "empty" | "no-results";
}

// Two distinct messages, matching two distinct realities: "no
// documents exist at all yet" (has a CTA) vs. "documents exist, your
// search/filters just don't match any" (doesn't).
export function DocumentEmptyState({ variant }: DocumentEmptyStateProps) {
  if (variant === "no-results") {
    return (
      <EmptyState
        icon={FileX2}
        title="No documents match your search"
        description="Try adjusting your search or filters."
      />
    );
  }

  return (
    <EmptyState
      icon={FileX2}
      title="No documents yet"
      description="Get started by uploading a patient's first document."
      action={
        <Button asChild size="sm">
          <Link href="/dashboard/documents/upload">
            <Upload className="size-4" />
            Upload Document
          </Link>
        </Button>
      }
    />
  );
}
