import {
  CalendarClock,
  FileStack,
  FileText,
  History,
  Stethoscope,
  Users,
  UsersRound,
  type LucideIcon,
} from "lucide-react";

import { DashboardCard } from "@/components/dashboard/dashboard-card";
import { PageHeader } from "@/components/dashboard/page-header";

export const metadata = { title: "Dashboard" };

interface QuickLink {
  title: string;
  description: string;
  href: string;
  icon: LucideIcon;
}

// Placeholder links only — matches `config/navigation.ts`'s sidebar
// entries exactly, none of these routes have real pages yet (see this
// module's own "Do NOT implement business pages" scope). Kept local to
// this page rather than in `config/navigation.ts` since it's a curated
// subset with dashboard-specific copy, not the full nav.
const quickLinks: QuickLink[] = [
  {
    title: "Patients",
    description: "Manage patient records.",
    href: "/dashboard/patients",
    icon: Users,
  },
  {
    title: "Appointments",
    description: "Schedule and manage visits.",
    href: "/dashboard/appointments",
    icon: CalendarClock,
  },
  {
    title: "Visits",
    description: "Track patient encounters.",
    href: "/dashboard/visits",
    icon: Stethoscope,
  },
  {
    title: "Clinical Notes",
    description: "Document clinical findings.",
    href: "/dashboard/clinical-notes",
    icon: FileText,
  },
  {
    title: "Documents",
    description: "Store and organize medical files.",
    href: "/dashboard/documents",
    icon: FileStack,
  },
  {
    title: "Timeline",
    description: "View a patient's care history.",
    href: "/dashboard/timeline",
    icon: History,
  },
  {
    title: "Family Access",
    description: "Manage caregiver permissions.",
    href: "/dashboard/family-access",
    icon: UsersRound,
  },
];

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Welcome to DrAssist"
        description="Your workspace will grow here as each module comes online."
      />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {quickLinks.map((link) => (
          <DashboardCard key={link.href} badge="Coming soon" {...link} />
        ))}
      </div>
    </div>
  );
}
