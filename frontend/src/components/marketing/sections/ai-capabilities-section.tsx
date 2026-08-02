import { Sparkles } from "lucide-react";

import { SectionHeading } from "@/components/marketing/section-heading";
import { Badge } from "@/components/ui/badge";
import { aiCapabilities } from "@/content/marketing/ai-capabilities";

export function AiCapabilitiesSection() {
  return (
    <section className="container py-20 sm:py-28">
      <div className="rounded-2xl border bg-gradient-to-br from-primary/5 via-background to-background p-8 sm:p-12">
        <div className="flex flex-col items-center gap-4 text-center">
          <Badge variant="outline" className="gap-1.5">
            <Sparkles className="size-3.5" aria-hidden="true" />
            Coming Soon
          </Badge>
          <SectionHeading
            title="AI built into your clinical workflow"
            description="AI capabilities are in active development — designed to assist, never replace, clinical judgment."
          />
        </div>
        <div className="mt-12 grid gap-6 sm:grid-cols-3">
          {aiCapabilities.map((item) => (
            <div key={item.title} className="rounded-lg border bg-background/60 p-5">
              <h3 className="font-semibold">{item.title}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{item.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
