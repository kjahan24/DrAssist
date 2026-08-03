import {
  Activity,
  CalendarClock,
  ClipboardList,
  FileStack,
  FileText,
  FlaskConical,
  Pill,
  ShieldAlert,
  Stethoscope,
  UserPlus,
  type LucideIcon,
} from "lucide-react";

import type { TimelineEventType } from "@/lib/mock/timeline";

// Presentational only (icon + accent color per event type) — kept out of
// `lib/mock/timeline.ts` the same way `DocumentPreview` keeps its
// mime-type-to-icon mapping out of `lib/mock/documents.ts`. Shared by
// `TimelineEvent` (the full Timeline View's icon-in-circle) and
// `TimelineCard` (Compact View's inline icon).
const EVENT_ICON: Record<TimelineEventType, LucideIcon> = {
  patient_registration: UserPlus,
  appointment: CalendarClock,
  visit: Stethoscope,
  clinical_note: FileText,
  soap_note: ClipboardList,
  lab_report: FlaskConical,
  prescription: Pill,
  document: FileStack,
  allergy: ShieldAlert,
  medication: Pill,
  medical_condition: Activity,
};

const EVENT_COLOR: Record<TimelineEventType, string> = {
  patient_registration: "bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-300",
  appointment: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  visit: "bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300",
  clinical_note: "bg-violet-100 text-violet-700 dark:bg-violet-950 dark:text-violet-300",
  soap_note: "bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-300",
  lab_report: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  prescription: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  document: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  allergy: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
  medication: "bg-teal-100 text-teal-700 dark:bg-teal-950 dark:text-teal-300",
  medical_condition: "bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-300",
};

export function getTimelineEventIcon(type: TimelineEventType): LucideIcon {
  return EVENT_ICON[type];
}

export function getTimelineEventColorClass(type: TimelineEventType): string {
  return EVENT_COLOR[type];
}
