import { env } from "@/config/env";

export const siteConfig = {
  name: env.NEXT_PUBLIC_APP_NAME,
  description:
    "DrAssist is a multi-tenant clinical operations platform for individual doctors, clinics, hospitals, and healthcare networks — EMR, scheduling, documents, and care team collaboration in one place.",
  url: env.NEXT_PUBLIC_SITE_URL,
  ogImage: `${env.NEXT_PUBLIC_SITE_URL}/og-image.png`,
  keywords: [
    "healthcare SaaS",
    "EMR",
    "electronic medical records",
    "clinic management software",
    "hospital software",
    "patient scheduling",
    "medical practice management",
  ],
  links: {
    // Placeholders — no real organization profiles exist yet; update when
    // they do.
    twitter: "https://twitter.com",
    linkedin: "https://linkedin.com",
    github: "https://github.com",
  },
  contactEmail: "hello@drassist.example",
} as const;
