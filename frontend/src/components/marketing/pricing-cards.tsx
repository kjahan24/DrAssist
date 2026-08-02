import Link from "next/link";
import { Check } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import type { PricingTier } from "@/content/marketing/pricing";
import { cn } from "@/lib/utils";

export function PricingCards({ tiers }: { tiers: PricingTier[] }) {
  return (
    <div className="grid gap-6 lg:grid-cols-3">
      {tiers.map((tier) => (
        <Card
          key={tier.name}
          className={cn(
            "flex flex-col",
            tier.highlighted && "border-primary shadow-lg ring-1 ring-primary",
          )}
        >
          <CardHeader className="space-y-2">
            {tier.highlighted && (
              <span className="w-fit rounded-full bg-primary px-3 py-1 text-xs font-medium text-primary-foreground">
                Most Popular
              </span>
            )}
            <h3 className="text-xl font-semibold">{tier.name}</h3>
            <p className="text-sm text-muted-foreground">{tier.description}</p>
            <div className="pt-2">
              <span className="text-3xl font-bold">{tier.price}</span>
            </div>
            <p className="text-xs text-muted-foreground">{tier.priceDetail}</p>
          </CardHeader>
          <CardContent className="flex-1">
            <ul className="space-y-3">
              {tier.features.map((feature) => (
                <li key={feature} className="flex items-start gap-2 text-sm">
                  <Check className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
                  <span>{feature}</span>
                </li>
              ))}
            </ul>
          </CardContent>
          <CardFooter>
            <Button asChild className="w-full" variant={tier.highlighted ? "default" : "outline"}>
              <Link href={tier.ctaHref}>{tier.cta}</Link>
            </Button>
          </CardFooter>
        </Card>
      ))}
    </div>
  );
}
