import type { Metadata } from "next";

import { CtaSection } from "@/components/marketing/cta-section";
import { FaqAccordion } from "@/components/marketing/faq-accordion";
import { SectionHeading } from "@/components/marketing/section-heading";
import { faqItems } from "@/content/marketing/faq";
import { buildMetadata } from "@/lib/seo";

export const metadata: Metadata = buildMetadata({
  title: "FAQ",
  description: "Answers to common questions about DrAssist.",
  path: "/faq",
});

export default function FaqPage() {
  return (
    <>
      <section className="container py-20 sm:py-28">
        <SectionHeading titleAs="h1" eyebrow="FAQ" title="Frequently asked questions" />
        <div className="mx-auto mt-12 max-w-2xl">
          <FaqAccordion items={faqItems} />
        </div>
      </section>
      <CtaSection
        title="Still have questions?"
        description="Reach out and our team will get back to you."
        primaryCta={{ label: "Contact Us", href: "/contact" }}
      />
    </>
  );
}
