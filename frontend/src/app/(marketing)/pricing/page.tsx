import type { Metadata } from "next";

import { CtaSection } from "@/components/marketing/cta-section";
import { FaqAccordion } from "@/components/marketing/faq-accordion";
import { PricingCards } from "@/components/marketing/pricing-cards";
import { SectionHeading } from "@/components/marketing/section-heading";
import { faqItems } from "@/content/marketing/faq";
import { pricingTiers } from "@/content/marketing/pricing";
import { buildMetadata } from "@/lib/seo";

export const metadata: Metadata = buildMetadata({
  title: "Pricing",
  description:
    "Simple, transparent plans for individual doctors, clinics, and healthcare networks.",
  path: "/pricing",
});

export default function PricingPage() {
  return (
    <>
      <section className="container py-20 sm:py-28">
        <SectionHeading
          titleAs="h1"
          eyebrow="Pricing"
          title="Plans that grow with your practice"
          description="Every plan includes the full clinical record, scheduling, and access-control foundation. Talk to us for a plan tailored to your organization."
        />
      </section>
      <div className="container pb-24">
        <PricingCards tiers={pricingTiers} />
      </div>
      <section className="border-t bg-muted/30 py-20 sm:py-28">
        <div className="container">
          <SectionHeading eyebrow="Pricing FAQ" title="Common questions about pricing" />
          <div className="mx-auto mt-12 max-w-2xl">
            <FaqAccordion items={faqItems} />
          </div>
        </div>
      </section>
      <CtaSection
        title="Ready to talk pricing?"
        description="Every plan is tailored to your organization's size and needs."
        primaryCta={{ label: "Contact Sales", href: "/contact" }}
      />
    </>
  );
}
