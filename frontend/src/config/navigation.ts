import {
  Activity,
  Bell,
  Building2,
  CalendarClock,
  CalendarDays,
  ClipboardList,
  FileStack,
  FileText,
  FlaskConical,
  HelpCircle,
  History,
  LayoutDashboard,
  ListChecks,
  Mail,
  Microscope,
  Paperclip,
  Pill,
  ScrollText,
  Settings,
  ShieldCheck,
  Split,
  Stethoscope,
  Thermometer,
  UserSquare2,
  Users,
  UsersRound,
} from "lucide-react";

import type { NavGroup } from "@/types/navigation";

// The complete information architecture for the platform, one entry per
// backend module (`backend/app/modules/*`) plus the Dashboard overview and
// Settings. Routes under each item don't have pages yet — see this task's
// own "Do NOT implement business modules yet" scope — but the shape here
// is what every future feature-module page will slot into, so the nav
// itself only needs building once. Grouping mirrors the module tiers in
// `docs/backend-architecture/03_module_architecture.md`.
export const navigation: NavGroup[] = [
  {
    title: "Overview",
    items: [{ title: "Dashboard", href: "/dashboard", icon: LayoutDashboard }],
  },
  {
    title: "Patients",
    items: [
      { title: "Patients", href: "/dashboard/patients", icon: Users },
      { title: "Visits", href: "/dashboard/visits", icon: CalendarDays },
      { title: "Timeline", href: "/dashboard/timeline", icon: History },
      { title: "Patient History", href: "/dashboard/patient-history", icon: ScrollText },
    ],
  },
  {
    title: "Clinical",
    items: [
      { title: "Clinical Notes", href: "/dashboard/clinical-notes", icon: FileText },
      { title: "SOAP Notes", href: "/dashboard/soap-notes", icon: ClipboardList },
      { title: "Vital Signs", href: "/dashboard/vital-signs", icon: Thermometer },
      { title: "Chief Complaints", href: "/dashboard/chief-complaints", icon: Stethoscope },
      { title: "Diagnoses", href: "/dashboard/diagnoses", icon: Activity },
      { title: "Procedures", href: "/dashboard/procedures", icon: ListChecks },
      { title: "Clinical Reasoning", href: "/dashboard/clinical-reasoning", icon: Split },
      {
        title: "Differential Diagnosis",
        href: "/dashboard/differential-diagnosis",
        icon: Split,
      },
      { title: "ICD-10 Coding", href: "/dashboard/icd10-coding", icon: FileStack },
      { title: "Doctor Reviews", href: "/dashboard/doctor-reviews", icon: UserSquare2 },
    ],
  },
  {
    title: "Orders",
    items: [
      { title: "Prescriptions", href: "/dashboard/prescriptions", icon: Pill },
      { title: "Lab Orders", href: "/dashboard/lab-orders", icon: FlaskConical },
      { title: "Lab Results", href: "/dashboard/lab-results", icon: Microscope },
    ],
  },
  {
    title: "Scheduling",
    items: [
      { title: "Appointments", href: "/dashboard/appointments", icon: CalendarClock },
      { title: "Schedule", href: "/dashboard/schedule", icon: CalendarDays },
    ],
  },
  {
    title: "Records",
    items: [
      { title: "Documents", href: "/dashboard/documents", icon: FileStack },
      { title: "Attachments", href: "/dashboard/attachments", icon: Paperclip },
    ],
  },
  {
    title: "People & Access",
    items: [
      { title: "Doctors", href: "/dashboard/doctors", icon: UserSquare2 },
      { title: "Organizations", href: "/dashboard/organizations", icon: Building2 },
      { title: "Family Access", href: "/dashboard/family", icon: UsersRound },
      { title: "Users & Roles", href: "/dashboard/access-control", icon: ShieldCheck },
    ],
  },
  {
    title: "System",
    items: [
      { title: "Notifications", href: "/dashboard/notifications", icon: Bell },
      { title: "Audit Log", href: "/dashboard/audit-logs", icon: ScrollText },
      { title: "Settings", href: "/dashboard/settings", icon: Settings },
      {
        // A toggle-only parent (its own `href` is never rendered as a
        // link — see `components/dashboard/sidebar-item.tsx`) — the one
        // deliberate example of nested navigation in this nav, and the
        // only genuinely new item this module adds. Its children point
        // at real, already-built marketing pages rather than yet more
        // placeholder dead links.
        title: "Help",
        href: "/dashboard/help",
        icon: HelpCircle,
        items: [
          { title: "FAQ", href: "/faq", icon: HelpCircle },
          { title: "Contact Support", href: "/contact", icon: Mail },
        ],
      },
    ],
  },
];
