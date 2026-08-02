import { Building2, KeyRound, Lock, ScrollText, ShieldCheck, type LucideIcon } from "lucide-react";

export interface SecurityHighlight {
  title: string;
  description: string;
  icon: LucideIcon;
}

// Architectural facts, not compliance certifications — DrAssist does not
// claim HIPAA/SOC2/ISO certification anywhere in this site; these
// describe how the platform is actually built.
export const securityHighlights: SecurityHighlight[] = [
  {
    title: "Multi-Tenant Isolation",
    description:
      "Every organization's data is scoped and isolated at the data layer — no cross-tenant access is possible.",
    icon: Building2,
  },
  {
    title: "Role-Based Access Control",
    description: "Fine-grained permissions ensure each user only ever sees what their role allows.",
    icon: ShieldCheck,
  },
  {
    title: "Full Audit Trail",
    description:
      "Every access and change to patient data is logged for accountability and compliance review.",
    icon: ScrollText,
  },
  {
    title: "Encrypted Credentials",
    description: "Passwords are hashed, never stored in plain text.",
    icon: Lock,
  },
  {
    title: "Secure Session Authentication",
    description: "Every request is authorized against a revocable, server-validated session.",
    icon: KeyRound,
  },
];
