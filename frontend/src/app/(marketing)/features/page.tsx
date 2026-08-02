import type { Metadata } from "next";

import { CtaSection } from "@/components/marketing/cta-section";
import { FeatureGrid } from "@/components/marketing/feature-grid";
import { SectionHeading } from "@/components/marketing/section-heading";
import { features, type FeatureCategory } from "@/content/marketing/features";
import { buildMetadata } from "@/lib/seo";

export const metadata: Metadata = buildMetadata({
  title: "Features",
  description:
    "Explore DrAssist's complete platform capabilities — EMR, scheduling, documents, access control, and more.",
  path: "/features",
});

const CATEGORY_ORDER: FeatureCategory[] = [
  "Clinical",
  "Operations",
  "Security & Compliance",
  "Platform",
  "AI",
];

export default function FeaturesPage() {
  return (
    <>
      <section className="container py-20 sm:py-28">
        <SectionHeading
          titleAs="h1"
          eyebrow="Features"
          title="A complete clinical operations platform"
          description="Every module below is part of the same connected system — built to work together, not bolted on."
        />
      </section>
      <div className="container space-y-16 pb-24">
        {CATEGORY_ORDER.map((category) => {
          const categoryFeatures = features.filter((feature) => feature.category === category);
          if (categoryFeatures.length === 0) return null;
          return (
            <div key={category}>
              <h2 className="text-xl font-semibold">{category}</h2>
              <div className="mt-6">
                <FeatureGrid features={categoryFeatures} />
              </div>
            </div>
          );
        })}
      </div>
      <CtaSection
        title="See DrAssist in action"
        description="Talk to our team about how DrAssist fits your organization."
        primaryCta={{ label: "Contact Us", href: "/contact" }}
        secondaryCta={{ label: "View Pricing", href: "/pricing" }}
      />
    </>
  );
}
