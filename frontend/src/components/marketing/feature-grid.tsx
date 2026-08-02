import { FeatureCard } from "@/components/marketing/feature-card";
import type { MarketingFeature } from "@/content/marketing/features";

interface FeatureGridProps {
  features: MarketingFeature[];
  limit?: number;
}

export function FeatureGrid({ features, limit }: FeatureGridProps) {
  const items = limit ? features.slice(0, limit) : features;

  return (
    <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((feature) => (
        <FeatureCard key={feature.title} feature={feature} />
      ))}
    </div>
  );
}
