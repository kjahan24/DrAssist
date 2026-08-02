import Link from "next/link";
import { Stethoscope } from "lucide-react";

import { siteConfig } from "@/config/site";

export function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-muted/30 p-4">
      <Link
        href="/"
        className="flex items-center gap-2 text-lg font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <Stethoscope className="size-6 text-primary" aria-hidden="true" />
        {siteConfig.name}
      </Link>
      <div className="w-full max-w-sm">{children}</div>
    </div>
  );
}
