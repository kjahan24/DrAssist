import type { Metadata } from "next";

import { siteConfig } from "@/config/site";

interface BuildMetadataOptions {
  title: string;
  description?: string;
  path?: string;
  noIndex?: boolean;
}

// Every marketing page calls this once instead of hand-rolling
// OpenGraph/Twitter/canonical boilerplate — keeps the shape (and the
// absolute-URL logic) in one place.
//
// `title` is passed through as-is for the <title> tag, which goes through
// the root layout's `template` (`%s | DrAssist`) automatically — so
// callers must pass the page title *alone*, never a version that already
// includes "DrAssist", or the rendered title doubles up (e.g. "DrAssist —
// ... | DrAssist"). OpenGraph/Twitter titles don't get that templating for
// free (Next's metadata API only templates the <title> tag), so this
// builds the branded version explicitly, deduping if `title` happens to
// already contain the site name.
export function buildMetadata({
  title,
  description = siteConfig.description,
  path = "/",
  noIndex = false,
}: BuildMetadataOptions): Metadata {
  const url = new URL(path, siteConfig.url).toString();
  const socialTitle = title.includes(siteConfig.name) ? title : `${title} | ${siteConfig.name}`;

  return {
    title,
    description,
    alternates: {
      canonical: url,
    },
    openGraph: {
      title: socialTitle,
      description,
      url,
      siteName: siteConfig.name,
      type: "website",
      images: [{ url: siteConfig.ogImage, width: 1200, height: 630, alt: siteConfig.name }],
    },
    twitter: {
      card: "summary_large_image",
      title: socialTitle,
      description,
      images: [siteConfig.ogImage],
    },
    robots: noIndex ? { index: false, follow: false } : { index: true, follow: true },
  };
}

// schema.org Organization structured data, rendered once from the
// marketing layout via a JSON-LD <script> tag.
export function organizationJsonLd() {
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: siteConfig.name,
    url: siteConfig.url,
    description: siteConfig.description,
    sameAs: [siteConfig.links.twitter, siteConfig.links.linkedin, siteConfig.links.github],
  };
}
