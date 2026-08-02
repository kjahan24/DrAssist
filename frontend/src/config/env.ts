import { z } from "zod";

// Validates process.env once at module load so a missing/misconfigured
// variable fails fast at build/start time instead of surfacing as a
// confusing runtime error deep in a component.
const envSchema = z.object({
  NEXT_PUBLIC_APP_NAME: z.string().min(1),
  NEXT_PUBLIC_API_BASE_URL: z.string().url(),
  // Public site origin — needed for absolute URLs the API base URL can't
  // supply (canonical links, OpenGraph images, sitemap.xml). Added for the
  // Landing Website module; defaults to local dev so existing setups don't
  // need an env change to keep building.
  NEXT_PUBLIC_SITE_URL: z.string().url().default("http://localhost:3000"),
  NODE_ENV: z.enum(["development", "production", "test"]).default("development"),
});

export const env = envSchema.parse({
  NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME,
  NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
  NEXT_PUBLIC_SITE_URL: process.env.NEXT_PUBLIC_SITE_URL,
  NODE_ENV: process.env.NODE_ENV,
});
