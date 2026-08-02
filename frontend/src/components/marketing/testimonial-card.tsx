import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Card, CardContent } from "@/components/ui/card";
import type { Testimonial } from "@/content/marketing/testimonials";

export function TestimonialCard({ testimonial }: { testimonial: Testimonial }) {
  return (
    <Card className="h-full">
      <CardContent className="flex h-full flex-col justify-between gap-6 pt-6">
        <p className="text-sm leading-relaxed text-foreground">&ldquo;{testimonial.quote}&rdquo;</p>
        <div className="flex items-center gap-3">
          <Avatar>
            <AvatarFallback>{testimonial.initials}</AvatarFallback>
          </Avatar>
          <p className="text-sm font-medium">{testimonial.role}</p>
        </div>
      </CardContent>
    </Card>
  );
}
