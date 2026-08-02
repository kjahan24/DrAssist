import type { Metadata } from "next";

import { CtaSection } from "@/components/marketing/cta-section";
import { SectionHeading } from "@/components/marketing/section-heading";
import { SolutionCard } from "@/components/marketing/solution-card";
import { solutions } from "@/content/marketing/solutions";
import { buildMetadata } from "@/lib/seo";

export const metadata: Metadata = buildMetadata({
  title: "Solutions",
  description:
    "DrAssist for individual doctors, clinics, hospitals, diagnostic centers, and healthcare networks.",
  path: "/solutions",
});

export default function SolutionsPage() {
  return (
    <>
      <section className="container py-20 sm:py-28">
        <SectionHeading
          titleAs="h1"
          eyebrow="Solutions"
          title="Built for every kind of care team"
          description="From a solo practice to a multi-site healthcare network, DrAssist scales with how you deliver care."
        />
      </section>
      <div className="container grid gap-8 pb-24 md:grid-cols-2">
        {solutions.map((solution) => (
          <SolutionCard key={solution.slug} solution={solution} />
        ))}
      </div>
      <CtaSection
        title="Not sure which fits your organization?"
        description="Tell us about your team and we'll help you find the right setup."
        primaryCta={{ label: "Talk to Us", href: "/contact" }}
      />
    </>
  );
}
