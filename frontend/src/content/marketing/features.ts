import {
  Bell,
  CalendarClock,
  CalendarDays,
  Code2,
  FileStack,
  FileText,
  History,
  ScrollText,
  Search,
  ShieldCheck,
  Sparkles,
  UsersRound,
  type LucideIcon,
} from "lucide-react";

// Plain, typed data — not fetched from anywhere yet, but shaped so a
// future CMS or `/api/v1/*`-backed endpoint can replace this module
// without any page needing to change.
export type FeatureCategory =
  "Clinical" | "Operations" | "Security & Compliance" | "Platform" | "AI";

export interface MarketingFeature {
  title: string;
  description: string;
  icon: LucideIcon;
  category: FeatureCategory;
  status: "available" | "coming-soon";
}

export const features: MarketingFeature[] = [
  {
    title: "Electronic Medical Records",
    description:
      "Clinical notes, SOAP notes, diagnoses, vital signs, and prescriptions in one structured record per patient.",
    icon: FileText,
    category: "Clinical",
    status: "available",
  },
  {
    title: "Appointments",
    description: "A full appointment lifecycle — book, confirm, check in, and complete visits.",
    icon: CalendarClock,
    category: "Operations",
    status: "available",
  },
  {
    title: "Scheduling & Availability",
    description: "Tenant-scoped doctor availability with configurable appointment slot durations.",
    icon: CalendarDays,
    category: "Operations",
    status: "available",
  },
  {
    title: "Notifications",
    description:
      "Event-driven notifications keep care teams and patients informed as records change.",
    icon: Bell,
    category: "Operations",
    status: "available",
  },
  {
    title: "Medical Documents",
    description: "Upload, categorize, and retrieve medical documents and attachments securely.",
    icon: FileStack,
    category: "Clinical",
    status: "available",
  },
  {
    title: "Personal Health Timeline",
    description: "A unified, chronological view of every clinical event across a patient's care.",
    icon: History,
    category: "Clinical",
    status: "available",
  },
  {
    title: "Family & Caregiver Access",
    description:
      "Controlled, revocable access for family members and caregivers to a patient's record.",
    icon: UsersRound,
    category: "Clinical",
    status: "available",
  },
  {
    title: "Audit Logs",
    description:
      "Every access and change to patient data is recorded for accountability and review.",
    icon: ScrollText,
    category: "Security & Compliance",
    status: "available",
  },
  {
    title: "Role-Based Access Control",
    description: "Fine-grained, role-based permissions scoped to your organization.",
    icon: ShieldCheck,
    category: "Security & Compliance",
    status: "available",
  },
  {
    title: "Search & Filtering",
    description:
      "Fast, structured search and filtering across patients, visits, and clinical records.",
    icon: Search,
    category: "Platform",
    status: "available",
  },
  {
    title: "REST APIs",
    description:
      "A documented REST API for every module, ready for integrations with your existing tools.",
    icon: Code2,
    category: "Platform",
    status: "available",
  },
  {
    title: "AI Clinical Assistant",
    description: "AI-assisted documentation and clinical insights, built directly into the record.",
    icon: Sparkles,
    category: "AI",
    status: "coming-soon",
  },
];
