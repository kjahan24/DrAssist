"use client";

import { useEffect } from "react";

import { ErrorState } from "@/components/shared/states/error-state";

// App Router's error boundary — catches render/rendering-lifecycle errors
// anywhere in the tree below it. Must be a Client Component.
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <ErrorState
        title="Something went wrong"
        description={error.message || "An unexpected error occurred."}
        onRetry={reset}
      />
    </div>
  );
}
