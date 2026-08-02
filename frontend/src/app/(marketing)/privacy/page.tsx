import type { Metadata } from "next";

import { LegalContent } from "@/components/marketing/legal-content";
import { siteConfig } from "@/config/site";
import { buildMetadata } from "@/lib/seo";

export const metadata: Metadata = buildMetadata({
  title: "Privacy Policy",
  description: `How ${siteConfig.name} collects, uses, and protects information.`,
  path: "/privacy",
});

export default function PrivacyPolicyPage() {
  return (
    <LegalContent
      title="Privacy Policy"
      lastUpdated="August 2026"
      intro={`This Privacy Policy describes how ${siteConfig.name} collects, uses, and protects information in connection with our platform.`}
      sections={[
        {
          heading: "Information We Collect",
          body: [
            "We collect information you provide directly, such as your name, email address, and organization details when you contact us or use the platform.",
            "For customers using the platform, we process clinical and administrative data that your organization enters and controls, in accordance with your agreement with us.",
          ],
        },
        {
          heading: "How We Use Information",
          body: [
            "We use information to operate and improve the platform, respond to inquiries, and communicate important updates about your account or our services.",
            "We do not sell personal information to third parties.",
          ],
        },
        {
          heading: "Data Security",
          body: [
            "The platform is built with multi-tenant data isolation, role-based access control, and audit logging as core architectural principles — not features added after the fact.",
            "No system can guarantee absolute security. We continuously work to protect information against unauthorized access, alteration, disclosure, or destruction.",
          ],
        },
        {
          heading: "Data Sharing",
          body: [
            "We do not share personal or clinical data with third parties except as necessary to provide the service, comply with the law, or with your explicit consent.",
          ],
        },
        {
          heading: "Your Rights",
          body: [
            "Depending on your jurisdiction, you may have rights to access, correct, or delete information we hold about you. Contact us to exercise these rights.",
          ],
        },
        {
          heading: "Cookies",
          body: [
            "We use essential cookies to keep you signed in and remember your preferences (such as light/dark theme). We do not use third-party advertising cookies.",
          ],
        },
        {
          heading: "Changes to This Policy",
          body: [
            'We may update this policy from time to time. Material changes will be reflected by an updated "Last updated" date above.',
          ],
        },
        {
          heading: "Contact Us",
          body: [`Questions about this policy can be sent to ${siteConfig.contactEmail}.`],
        },
      ]}
    />
  );
}
