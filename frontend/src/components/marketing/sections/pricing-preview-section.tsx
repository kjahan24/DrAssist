import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { PricingCards } from "@/components/marketing/pricing-cards";
import { SectionHeading } from "@/components/marketing/section-heading";
import { Button } from "@/components/ui/button";
import { pricingTiers } from "@/content/marketing/pricing";

export function PricingPreviewSection() {
  return (
    <section className="container py-20 sm:py-28">
      <SectionHeading
        eyebrow="Pricing"
        title="Plans that grow with your practice"
        description="From solo practitioners to healthcare networks."
      />
      <div className="mt-12">
        <PricingCards tiers={pricingTiers} />
      </div>
      <div className="mt-10 flex justify-center">
        <Button asChild variant="outline">
          <Link href="/pricing">
            See full pricing details
            <ArrowRight className="size-4" />
          </Link>
        </Button>
      </div>
    </section>
  );
}
