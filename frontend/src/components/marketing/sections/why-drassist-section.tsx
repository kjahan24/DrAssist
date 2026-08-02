import { SectionHeading } from "@/components/marketing/section-heading";
import { whyDrAssistPoints } from "@/content/marketing/why-drassist";

export function WhyDrAssistSection() {
  return (
    <section className="border-t bg-muted/30 py-20 sm:py-28">
      <div className="container">
        <SectionHeading
          eyebrow="Why DrAssist"
          title="Software that matches how care actually happens"
        />
        <div className="mt-12 grid gap-8 sm:grid-cols-2">
          {whyDrAssistPoints.map((point) => {
            const Icon = point.icon;
            return (
              <div key={point.title} className="flex gap-4">
                <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                  <Icon className="size-5 text-primary" aria-hidden="true" />
                </div>
                <div>
                  <h3 className="font-semibold">{point.title}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">{point.description}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
