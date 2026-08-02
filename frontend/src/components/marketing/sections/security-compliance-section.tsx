import { SectionHeading } from "@/components/marketing/section-heading";
import { SecurityGrid } from "@/components/marketing/security-grid";
import { securityHighlights } from "@/content/marketing/security";

export function SecurityComplianceSection() {
  return (
    <section className="container py-20 sm:py-28">
      <SectionHeading
        eyebrow="Security & Compliance"
        title="Built for healthcare from the ground up"
        description="Security isn't a feature we added — it's the foundation every module is built on."
      />
      <div className="mt-12">
        <SecurityGrid items={securityHighlights} />
      </div>
    </section>
  );
}
