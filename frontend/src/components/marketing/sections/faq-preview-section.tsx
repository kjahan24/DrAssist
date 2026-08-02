import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { FaqAccordion } from "@/components/marketing/faq-accordion";
import { SectionHeading } from "@/components/marketing/section-heading";
import { Button } from "@/components/ui/button";
import { faqItems } from "@/content/marketing/faq";

export function FaqPreviewSection() {
  return (
    <section className="border-t bg-muted/30 py-20 sm:py-28">
      <div className="container">
        <SectionHeading eyebrow="FAQ" title="Frequently asked questions" />
        <div className="mx-auto mt-12 max-w-2xl">
          <FaqAccordion items={faqItems.slice(0, 4)} />
        </div>
        <div className="mt-10 flex justify-center">
          <Button asChild variant="outline">
            <Link href="/faq">
              View all questions
              <ArrowRight className="size-4" />
            </Link>
          </Button>
        </div>
      </div>
    </section>
  );
}
