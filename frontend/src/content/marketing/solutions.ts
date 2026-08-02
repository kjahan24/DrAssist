import {
  Building2,
  Hospital,
  Microscope,
  Network,
  Stethoscope,
  type LucideIcon,
} from "lucide-react";

export interface Solution {
  slug: string;
  title: string;
  audience: string;
  description: string;
  icon: LucideIcon;
  highlights: string[];
}

export const solutions: Solution[] = [
  {
    slug: "individual-doctors",
    title: "Individual Doctors",
    audience: "Solo practitioners",
    description:
      "Run your practice without the overhead of enterprise software — patient records, scheduling, and documentation in one place.",
    icon: Stethoscope,
    highlights: [
      "Fast patient record entry",
      "Simple appointment scheduling",
      "Secure document storage",
    ],
  },
  {
    slug: "clinics",
    title: "Clinics",
    audience: "Multi-provider practices",
    description:
      "Coordinate care across multiple doctors and staff with shared scheduling, role-based access, and a unified patient record.",
    icon: Building2,
    highlights: [
      "Multi-provider scheduling",
      "Role-based access control",
      "Shared patient timeline",
    ],
  },
  {
    slug: "hospitals",
    title: "Hospitals",
    audience: "Multi-department facilities",
    description:
      "Support complex, multi-department workflows with organization-wide audit trails and fine-grained permissions.",
    icon: Hospital,
    highlights: [
      "Organization-wide audit logs",
      "Department-level access control",
      "Full clinical documentation suite",
    ],
  },
  {
    slug: "diagnostic-centers",
    title: "Diagnostic Centers",
    audience: "Labs & imaging",
    description:
      "Manage lab orders and results end-to-end, from request through to a structured, searchable result record.",
    icon: Microscope,
    highlights: ["Lab order lifecycle", "Structured lab results", "Fast record search"],
  },
  {
    slug: "healthcare-networks",
    title: "Healthcare Networks",
    audience: "Multi-organization groups",
    description:
      "Multi-tenant by design — every organization's data is isolated, with permissions and audit trails scoped per tenant.",
    icon: Network,
    highlights: [
      "True multi-tenant isolation",
      "Per-organization access control",
      "Consistent REST API across sites",
    ],
  },
];
