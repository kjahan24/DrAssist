import { SectionSkeleton } from "@/components/dashboard/section-skeleton";
import { Skeleton } from "@/components/ui/skeleton";

interface PageSkeletonProps {
  // Optional real heading text. Pages that render this as their loading
  // state (before any data — and therefore no page-specific title — is
  // available) must still ship a real <h1> in the server-rendered HTML;
  // omit it only when a real <h1> already exists elsewhere on the page.
  title?: string;
}

export function PageSkeleton({ title }: PageSkeletonProps = {}) {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        {title ? (
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        ) : (
          <Skeleton className="h-7 w-48" />
        )}
        <Skeleton className="h-4 w-72" />
      </div>
      <SectionSkeleton />
    </div>
  );
}
