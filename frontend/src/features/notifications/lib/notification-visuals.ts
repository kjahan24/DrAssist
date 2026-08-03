import {
  CalendarClock,
  ClipboardList,
  FileStack,
  FileText,
  FlaskConical,
  Pill,
  Settings,
  ShieldAlert,
  Stethoscope,
  UsersRound,
  type LucideIcon,
} from "lucide-react";

import type { NotificationCategory } from "@/lib/mock/notifications";

// Presentational only — kept out of `lib/mock/notifications.ts` the same
// way `features/timeline/lib/event-visuals.ts` keeps its own icon
// mapping out of `lib/mock/timeline.ts`. Shared by `NotificationCard`.
const CATEGORY_ICON: Record<NotificationCategory, LucideIcon> = {
  appointment: CalendarClock,
  visit: Stethoscope,
  clinical_note: FileText,
  soap_note: ClipboardList,
  lab_report: FlaskConical,
  prescription: Pill,
  medical_document: FileStack,
  family_invitation: UsersRound,
  system: Settings,
  security: ShieldAlert,
};

const CATEGORY_COLOR: Record<NotificationCategory, string> = {
  appointment: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  visit: "bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300",
  clinical_note: "bg-violet-100 text-violet-700 dark:bg-violet-950 dark:text-violet-300",
  soap_note: "bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-300",
  lab_report: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  prescription: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  medical_document: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  family_invitation: "bg-teal-100 text-teal-700 dark:bg-teal-950 dark:text-teal-300",
  system: "bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-300",
  security: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
};

export function getNotificationCategoryIcon(category: NotificationCategory): LucideIcon {
  return CATEGORY_ICON[category];
}

export function getNotificationCategoryColorClass(category: NotificationCategory): string {
  return CATEGORY_COLOR[category];
}
