import type { MetadataRoute } from "next";

import { siteConfig } from "@/config/site";

// The authenticated app (`/dashboard`, `/login`) is disallowed — nothing
// behind auth should be indexed, and `/login` is a bare form with no
// content worth crawling.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/dashboard", "/login"],
    },
    sitemap: new URL("/sitemap.xml", siteConfig.url).toString(),
  };
}
