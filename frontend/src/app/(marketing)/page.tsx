import type { Metadata } from "next";

import { CtaSection } from "@/components/marketing/cta-section";
import { AiCapabilitiesSection } from "@/components/marketing/sections/ai-capabilities-section";
import { FaqPreviewSection } from "@/components/marketing/sections/faq-preview-section";
import { FeaturesOverviewSection } from "@/components/marketing/sections/features-overview-section";
import { HeroSection } from "@/components/marketing/sections/hero-section";
import { PlatformModulesSection } from "@/components/marketing/sections/platform-modules-section";
import { PricingPreviewSection } from "@/components/marketing/sections/pricing-preview-section";
import { SecurityComplianceSection } from "@/components/marketing/sections/security-compliance-section";
import { TestimonialsSection } from "@/components/marketing/sections/testimonials-section";
import { TrustedBySection } from "@/components/marketing/sections/trusted-by-section";
import { WhyDrAssistSection } from "@/components/marketing/sections/why-drassist-section";
import { buildMetadata } from "@/lib/seo";

export const metadata: Metadata = buildMetadata({
  title: "Clinical Operations Platform for Modern Healthcare Teams",
  description:
    "EMR, scheduling, documents, and care team collaboration, built on a secure, multi-tenant foundation for doctors, clinics, hospitals, and healthcare networks.",
  path: "/",
});

export default function HomePage() {
  return (
    <>
      <HeroSection />
      <TrustedBySection />
      <FeaturesOverviewSection />
      <PlatformModulesSection />
      <AiCapabilitiesSection />
      <WhyDrAssistSection />
      <SecurityComplianceSection />
      <TestimonialsSection />
      <PricingPreviewSection />
      <FaqPreviewSection />
      <CtaSection
        title="Ready to bring your care team onto one platform?"
        description="Talk to us about your organization's needs — we'll help you find the right plan."
        primaryCta={{ label: "Get Started", href: "/contact" }}
        secondaryCta={{ label: "View Pricing", href: "/pricing" }}
      />
    </>
  );
}
