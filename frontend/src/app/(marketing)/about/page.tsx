import type { Metadata } from "next";

import { CtaSection } from "@/components/marketing/cta-section";
import { SectionHeading } from "@/components/marketing/section-heading";
import { whyDrAssistPoints } from "@/content/marketing/why-drassist";
import { buildMetadata } from "@/lib/seo";

export const metadata: Metadata = buildMetadata({
  title: "About",
  description:
    "DrAssist's mission is to give healthcare teams one connected platform instead of a dozen disconnected tools.",
  path: "/about",
});

export default function AboutPage() {
  return (
    <>
      <section className="container py-20 sm:py-28">
        <SectionHeading
          titleAs="h1"
          eyebrow="About DrAssist"
          title="Healthcare software built around how care actually happens"
          description="We built DrAssist because clinical teams deserve one connected platform, not a patchwork of disconnected tools stitched together with spreadsheets and manual handoffs."
        />
      </section>
      <section className="container pb-24">
        <div className="mx-auto max-w-3xl space-y-6 text-muted-foreground">
          <p>
            DrAssist started from a simple observation: most clinical software is built module by
            module, acquired and bolted together over time. The result is fragile integrations,
            inconsistent permissions, and data that doesn&apos;t move cleanly between systems.
          </p>
          <p>
            We took a different approach — designing every module, from patient records to
            scheduling to access control, on one shared foundation from day one. That means a
            consistent experience for your team and a single source of truth for your data.
          </p>
        </div>
        <div className="mx-auto mt-16 grid max-w-4xl gap-8 sm:grid-cols-2">
          {whyDrAssistPoints.map((point) => {
            const Icon = point.icon;
            return (
              <div key={point.title} className="flex gap-4">
                <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                  <Icon className="size-5 text-primary" aria-hidden="true" />
                </div>
                <div>
                  <h3 className="font-semibold">{point.title}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">{point.description}</p>
                </div>
              </div>
            );
          })}
        </div>
      </section>
      <CtaSection
        title="Want to learn more?"
        description="We'd love to hear about your organization and how DrAssist can help."
        primaryCta={{ label: "Get in Touch", href: "/contact" }}
      />
    </>
  );
}
