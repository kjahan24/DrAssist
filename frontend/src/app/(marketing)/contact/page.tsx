import type { Metadata } from "next";

import { ContactForm } from "@/components/marketing/contact-form";
import { SectionHeading } from "@/components/marketing/section-heading";
import { siteConfig } from "@/config/site";
import { buildMetadata } from "@/lib/seo";

export const metadata: Metadata = buildMetadata({
  title: "Contact",
  description: "Get in touch with the DrAssist team.",
  path: "/contact",
});

export default function ContactPage() {
  return (
    <section className="container py-20 sm:py-28">
      <SectionHeading
        titleAs="h1"
        eyebrow="Contact"
        title="Let's talk about your organization"
        description="Tell us a bit about your team and we'll follow up to find the right plan."
      />
      <div className="mx-auto mt-12 grid max-w-4xl gap-8 lg:grid-cols-2">
        <ContactForm />
        <div className="space-y-6">
          <div>
            <h3 className="font-semibold">Email</h3>
            <p className="mt-1 text-sm text-muted-foreground">{siteConfig.contactEmail}</p>
          </div>
          <div>
            <h3 className="font-semibold">What happens next?</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Our team will follow up to learn more about your organization and help you find the
              right plan — usually within one business day.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
