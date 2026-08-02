import type { Metadata } from "next";
import { Briefcase } from "lucide-react";

import { EmptyState } from "@/components/shared/states/empty-state";
import { buildMetadata } from "@/lib/seo";

export const metadata: Metadata = buildMetadata({
  title: "Careers",
  description: "Open roles at DrAssist — coming soon.",
  path: "/careers",
});

// Placeholder only — per this module's explicit scope.
export default function CareersPage() {
  return (
    <section className="container flex min-h-[50vh] items-center justify-center py-20">
      <EmptyState
        titleAs="h1"
        icon={Briefcase}
        title="No open roles yet"
        description="We're not hiring right now, but check back — open roles will be listed here as they become available."
      />
    </section>
  );
}
