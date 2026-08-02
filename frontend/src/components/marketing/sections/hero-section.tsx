import Link from "next/link";
import { ArrowRight, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";

export function HeroSection() {
  return (
    <section className="relative overflow-hidden">
      <div
        aria-hidden="true"
        className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,hsl(var(--primary)/0.15),transparent)]"
      />
      <div className="container flex flex-col items-center gap-6 py-24 text-center sm:py-32">
        <div className="inline-flex items-center gap-2 rounded-full border bg-background px-4 py-1.5 text-sm text-muted-foreground">
          <Sparkles className="size-3.5 text-primary" aria-hidden="true" />
          AI-assisted clinical tools, coming soon
        </div>
        <h1 className="max-w-3xl text-4xl font-bold tracking-tight sm:text-6xl">
          The clinical operations platform for modern healthcare teams
        </h1>
        <p className="max-w-2xl text-lg text-muted-foreground sm:text-xl">
          EMR, scheduling, documents, and care team collaboration — built on a secure, multi-tenant
          foundation for doctors, clinics, hospitals, and healthcare networks.
        </p>
        <div className="flex flex-col gap-3 sm:flex-row">
          <Button asChild size="lg">
            <Link href="/contact">
              Get Started
              <ArrowRight className="size-4" />
            </Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <Link href="/features">Explore Features</Link>
          </Button>
        </div>
      </div>
    </section>
  );
}
