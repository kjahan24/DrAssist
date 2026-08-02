import type { Metadata } from "next";
import { Newspaper } from "lucide-react";

import { EmptyState } from "@/components/shared/states/empty-state";
import { buildMetadata } from "@/lib/seo";

export const metadata: Metadata = buildMetadata({
  title: "Blog",
  description: "Insights and updates from the DrAssist team — coming soon.",
  path: "/blog",
});

// Placeholder only — per this module's explicit scope.
export default function BlogPage() {
  return (
    <section className="container flex min-h-[50vh] items-center justify-center py-20">
      <EmptyState
        titleAs="h1"
        icon={Newspaper}
        title="Blog coming soon"
        description="We're working on insights and updates from the DrAssist team. Check back soon."
      />
    </section>
  );
}
