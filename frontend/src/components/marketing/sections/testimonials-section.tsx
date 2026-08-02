import { SectionHeading } from "@/components/marketing/section-heading";
import { TestimonialCard } from "@/components/marketing/testimonial-card";
import { testimonials } from "@/content/marketing/testimonials";

export function TestimonialsSection() {
  return (
    <section className="border-t bg-muted/30 py-20 sm:py-28">
      <div className="container">
        <SectionHeading
          eyebrow="Testimonials"
          title="What care teams are saying"
          description="Sample feedback — real customer stories will appear here as they come in."
        />
        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {testimonials.map((testimonial) => (
            <TestimonialCard key={testimonial.role} testimonial={testimonial} />
          ))}
        </div>
      </div>
    </section>
  );
}
