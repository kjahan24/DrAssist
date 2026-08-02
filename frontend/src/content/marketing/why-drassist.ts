import { Building2, Code2, Layers, UsersRound, type LucideIcon } from "lucide-react";

export interface WhyPoint {
  title: string;
  description: string;
  icon: LucideIcon;
}

export const whyDrAssistPoints: WhyPoint[] = [
  {
    title: "One platform, not a dozen tools",
    description:
      "EMR, scheduling, documents, and access control share one data model — no fragile integrations to maintain.",
    icon: Layers,
  },
  {
    title: "Multi-tenant from day one",
    description:
      "Every organization's data is isolated at the data layer, not bolted on with application-level checks.",
    icon: Building2,
  },
  {
    title: "API-first architecture",
    description:
      "Every module is available over a documented REST API, so you're never locked into our UI alone.",
    icon: Code2,
  },
  {
    title: "Built for teams, not just individuals",
    description:
      "Role-based access and family/caregiver sharing reflect how care actually gets delivered.",
    icon: UsersRound,
  },
];
