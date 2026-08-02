// No billing is implemented (by design — see this module's own scope).
// Prices are deliberately not numeric placeholders; every tier routes to
// `/contact` rather than a self-serve checkout that doesn't exist.
export interface PricingTier {
  name: string;
  description: string;
  price: string;
  priceDetail: string;
  cta: string;
  ctaHref: string;
  highlighted?: boolean;
  features: string[];
}

export const pricingTiers: PricingTier[] = [
  {
    name: "Starter",
    description: "For individual doctors and small practices getting started.",
    price: "Contact us",
    priceDetail: "Simple, transparent pricing for small teams",
    cta: "Get Started",
    ctaHref: "/contact",
    features: [
      "Up to 3 users",
      "Core EMR & scheduling",
      "Medical document storage",
      "Email support",
    ],
  },
  {
    name: "Professional",
    description: "For growing clinics that need more control and visibility.",
    price: "Contact us",
    priceDetail: "Built for multi-provider clinics",
    cta: "Get Started",
    ctaHref: "/contact",
    highlighted: true,
    features: [
      "Up to 25 users",
      "Everything in Starter",
      "Role-based access control",
      "Family & caregiver access",
      "Audit logs",
      "Priority support",
    ],
  },
  {
    name: "Enterprise",
    description: "For hospitals and healthcare networks with advanced needs.",
    price: "Custom",
    priceDetail: "Tailored to your organization",
    cta: "Contact Sales",
    ctaHref: "/contact",
    features: [
      "Unlimited users",
      "Everything in Professional",
      "Multi-organization support",
      "Dedicated onboarding",
      "SLA-backed support",
      "Custom integrations via REST API",
    ],
  },
];
