import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { FeatureGrid } from "@/components/marketing/feature-grid";
import { SectionHeading } from "@/components/marketing/section-heading";
import { Button } from "@/components/ui/button";
import { features } from "@/content/marketing/features";

export function FeaturesOverviewSection() {
  return (
    <section className="container py-20 sm:py-28">
      <SectionHeading
        eyebrow="Platform"
        title="Everything your care team needs, in one place"
        description="A complete set of clinical and operational tools, built as one connected platform instead of a dozen disconnected tools."
      />
      <div className="mt-12">
        <FeatureGrid features={features} limit={6} />
      </div>
      <div className="mt-10 flex justify-center">
        <Button asChild variant="outline">
          <Link href="/features">
            View all features
            <ArrowRight className="size-4" />
          </Link>
        </Button>
      </div>
    </section>
  );
}
