import Link from "next/link";
import { FileQuestion } from "lucide-react";

import { MarketingFooter } from "@/components/marketing/marketing-footer";
import { MarketingHeader } from "@/components/marketing/marketing-header";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Button } from "@/components/ui/button";

// Global 404 — Next.js always renders the ROOT not-found.tsx for URLs
// that match no route at all (route-group-nested not-found.tsx files only
// catch notFound() calls *within* that group), so this is the one place
// that needs to look right for every visitor, marketing or app. Wrapped
// in the marketing chrome since that's the shell reachable from any URL.
export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col">
      <MarketingHeader />
      <main className="flex flex-1 items-center justify-center p-4 py-24">
        <EmptyState
          titleAs="h1"
          icon={FileQuestion}
          title="Page not found"
          description="The page you're looking for doesn't exist or hasn't been built yet."
          action={
            <Button asChild size="sm">
              <Link href="/">Back to home</Link>
            </Button>
          }
        />
      </main>
      <MarketingFooter />
    </div>
  );
}
