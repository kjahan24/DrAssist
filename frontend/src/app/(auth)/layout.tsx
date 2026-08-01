import { Stethoscope } from "lucide-react";

import { siteConfig } from "@/config/site";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-muted/30 p-4">
      <div className="flex items-center gap-2 text-lg font-semibold">
        <Stethoscope className="size-6 text-primary" />
        {siteConfig.name}
      </div>
      <div className="w-full max-w-sm">{children}</div>
    </div>
  );
}
