import type { Metadata } from "next";

import { LegalContent } from "@/components/marketing/legal-content";
import { siteConfig } from "@/config/site";
import { buildMetadata } from "@/lib/seo";

export const metadata: Metadata = buildMetadata({
  title: "Terms of Service",
  description: `The terms that govern use of ${siteConfig.name}.`,
  path: "/terms",
});

export default function TermsOfServicePage() {
  return (
    <LegalContent
      title="Terms of Service"
      lastUpdated="August 2026"
      intro={`These Terms of Service govern your access to and use of ${siteConfig.name}. By using the platform, you agree to these terms.`}
      sections={[
        {
          heading: "Acceptance of Terms",
          body: [
            "By accessing or using the platform, you agree to be bound by these terms and any agreement in place between your organization and us.",
          ],
        },
        {
          heading: "Use of the Service",
          body: [
            "You may use the platform only for lawful purposes and in accordance with your organization's agreement with us.",
            "You are responsible for maintaining the confidentiality of your account credentials and for all activity under your account.",
          ],
        },
        {
          heading: "Account Responsibilities",
          body: [
            "Your organization is responsible for the accuracy of the data entered into the platform and for managing user access within your organization.",
          ],
        },
        {
          heading: "Intellectual Property",
          body: [
            `The platform, including its software and design, is owned by ${siteConfig.name} and protected by applicable intellectual property laws. Your organization retains ownership of the data it enters.`,
          ],
        },
        {
          heading: "Limitation of Liability",
          body: [
            `To the maximum extent permitted by law, ${siteConfig.name} is not liable for indirect, incidental, or consequential damages arising from use of the platform.`,
          ],
        },
        {
          heading: "Termination",
          body: [
            "Either party may terminate access to the platform in accordance with the terms of your organization's agreement with us.",
          ],
        },
        {
          heading: "Changes to These Terms",
          body: [
            "We may update these terms from time to time. Continued use of the platform after changes take effect constitutes acceptance of the updated terms.",
          ],
        },
        {
          heading: "Contact Us",
          body: [`Questions about these terms can be sent to ${siteConfig.contactEmail}.`],
        },
      ]}
    />
  );
}
