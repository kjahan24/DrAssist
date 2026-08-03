// Static navigation shortcuts for the Command Palette's "Quick Actions"
// group — plain UI configuration (the same category as
// `config/navigation.ts`), not mock business data, so it doesn't live in
// `lib/mock/`. Every href points at a real, already-built page from an
// earlier module; the palette only ever navigates to it (see this
// task's own "Quick navigation (UI)" wording) — it never performs a
// mutation itself.

export interface QuickAction {
  id: string;
  label: string;
  href: string;
}

export const QUICK_ACTIONS: QuickAction[] = [
  { id: "new-patient", label: "New Patient", href: "/dashboard/patients/new" },
  { id: "new-appointment", label: "New Appointment", href: "/dashboard/appointments/new" },
  { id: "new-visit", label: "New Visit", href: "/dashboard/visits/new" },
  { id: "new-clinical-note", label: "New Clinical Note", href: "/dashboard/clinical-notes/new" },
  { id: "new-soap-note", label: "New SOAP Note", href: "/dashboard/soap-notes/new" },
  { id: "new-prescription", label: "New Prescription", href: "/dashboard/prescriptions/new" },
  { id: "upload-document", label: "Upload Document", href: "/dashboard/documents/upload" },
  { id: "open-timeline", label: "Open Timeline", href: "/dashboard/timeline" },
  { id: "open-notifications", label: "Open Notifications", href: "/dashboard/notifications" },
  { id: "open-profile", label: "Open Profile", href: "/dashboard/profile" },
  { id: "open-organization", label: "Open Organization", href: "/dashboard/organization" },
];
