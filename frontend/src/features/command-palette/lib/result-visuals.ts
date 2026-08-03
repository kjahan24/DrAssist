import {
  Bell,
  CalendarClock,
  ClipboardList,
  FileStack,
  FileText,
  FlaskConical,
  History,
  Pill,
  Stethoscope,
  UserRound,
  UsersRound,
  type LucideIcon,
} from "lucide-react";

import type { SearchEntityType } from "@/features/command-palette/lib/global-search";

// Presentational only — kept out of the search aggregation layer the
// same way `features/timeline/lib/event-visuals.ts` keeps its own icon
// mapping out of `lib/mock/timeline.ts`.
const ENTITY_ICON: Record<SearchEntityType, LucideIcon> = {
  patient: UserRound,
  appointment: CalendarClock,
  visit: Stethoscope,
  clinical_note: FileText,
  soap_note: ClipboardList,
  lab_report: FlaskConical,
  prescription: Pill,
  document: FileStack,
  timeline_event: History,
  family_member: UsersRound,
  notification: Bell,
  organization_member: UsersRound,
};

const ENTITY_LABEL: Record<SearchEntityType, string> = {
  patient: "Patient",
  appointment: "Appointment",
  visit: "Visit",
  clinical_note: "Clinical Note",
  soap_note: "SOAP Note",
  lab_report: "Lab Report",
  prescription: "Prescription",
  document: "Document",
  timeline_event: "Timeline Event",
  family_member: "Family Member",
  notification: "Notification",
  organization_member: "Organization Member",
};

export function getSearchResultIcon(type: SearchEntityType): LucideIcon {
  return ENTITY_ICON[type];
}

export function getSearchEntityLabel(type: SearchEntityType): string {
  return ENTITY_LABEL[type];
}
