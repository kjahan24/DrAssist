import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { MarketingFeature } from "@/content/marketing/features";

export function FeatureCard({ feature }: { feature: MarketingFeature }) {
  const Icon = feature.icon;

  return (
    <Card className="h-full">
      <CardHeader className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10">
            <Icon className="size-5 text-primary" aria-hidden="true" />
          </div>
          {feature.status === "coming-soon" && <Badge variant="outline">Coming Soon</Badge>}
        </div>
        <h3 className="font-semibold">{feature.title}</h3>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">{feature.description}</p>
      </CardContent>
    </Card>
  );
}
