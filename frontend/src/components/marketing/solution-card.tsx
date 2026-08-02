import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { Solution } from "@/content/marketing/solutions";

export function SolutionCard({ solution }: { solution: Solution }) {
  const Icon = solution.icon;

  return (
    <Card id={solution.slug} className="scroll-mt-24">
      <CardHeader className="space-y-3">
        <div className="flex size-12 items-center justify-center rounded-lg bg-primary/10">
          <Icon className="size-6 text-primary" aria-hidden="true" />
        </div>
        <div>
          <p className="text-sm font-medium text-primary">{solution.audience}</p>
          <h3 className="text-xl font-semibold">{solution.title}</h3>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-muted-foreground">{solution.description}</p>
        <ul className="space-y-2">
          {solution.highlights.map((highlight) => (
            <li key={highlight} className="flex items-start gap-2 text-sm">
              <span
                className="mt-1.5 size-1.5 shrink-0 rounded-full bg-primary"
                aria-hidden="true"
              />
              <span>{highlight}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
