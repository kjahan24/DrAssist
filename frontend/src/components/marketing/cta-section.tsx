import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";

interface CtaLink {
  label: string;
  href: string;
}

interface CtaSectionProps {
  title: string;
  description?: string;
  primaryCta: CtaLink;
  secondaryCta?: CtaLink;
}

export function CtaSection({ title, description, primaryCta, secondaryCta }: CtaSectionProps) {
  return (
    <section className="border-t bg-muted/30">
      <div className="container flex flex-col items-center gap-6 py-20 text-center">
        <h2 className="max-w-2xl text-3xl font-semibold tracking-tight sm:text-4xl">{title}</h2>
        {description && <p className="max-w-xl text-lg text-muted-foreground">{description}</p>}
        <div className="flex flex-col gap-3 sm:flex-row">
          <Button asChild size="lg">
            <Link href={primaryCta.href}>
              {primaryCta.label}
              <ArrowRight className="size-4" />
            </Link>
          </Button>
          {secondaryCta && (
            <Button asChild size="lg" variant="outline">
              <Link href={secondaryCta.href}>{secondaryCta.label}</Link>
            </Button>
          )}
        </div>
      </div>
    </section>
  );
}
