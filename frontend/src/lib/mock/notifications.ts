// Temporary frontend mock repository for the Notifications Center
// (`app/(dashboard)/dashboard/notifications/*`). No backend API is
// consumed anywhere in this module — every function below reads from and
// writes to an in-memory array, standing in for the real backend
// `app.modules.notification` module (aggregate `Notification`) until its
// REST endpoints exist (`container.py` notes this module currently
// builds no HTTP layer at all — `api/schemas.py` exists for a future
// task).
//
// `priority`/`status` are grounded verbatim in the real domain enums
// (`app.modules.notification.domain.enums`). `status` follows the real
// entity's exact transition graph — `(Pending|Scheduled) -> Sent ->
// Delivered -> Read`, with `Cancelled`/`Expired` reachable only pre-Sent
// — never a simple boolean.
//
// Three deliberate departures from the real backend, each called out
// because nothing forced this shape but the task's own requirements:
//
//   1. **`NotificationCategory` (10 values) is a different, coarser
//      taxonomy than the real `NotificationType` enum** (8 values:
//      `appointment_reminder/appointment_confirmed/appointment_cancelled/
//      visit_completed/prescription_ready/lab_result_ready/general/
//      system`). The real enum tracks fine-grained *triggers*; this
//      task's "Notification Types" section asks for coarser
//      *source-module categories* instead, several of which
//      (`clinical_note`, `soap_note`, `medical_document`,
//      `family_invitation`, `security`) have no real `NotificationType`
//      member at all yet — those modules' own notification-producing
//      events aren't in the current enum. `category` is what this UI's
//      display/filtering is actually built around; the closest honest
//      mapping back to real `notification_type` values is documented
//      inline in `CATEGORY_TO_BACKEND_TYPE` below.
//   2. **"Mark as unread" has no real counterpart — the real domain
//      explicitly forbids it** ("Read notifications cannot become
//      unread", enforced structurally: `Read` has no outgoing edges in
//      `_ALLOWED_TRANSITIONS`). `markNotificationAsUnread()` is kept
//      anyway because it's a standard, expected notification-center
//      affordance this task explicitly asks for — implemented as the
//      one deliberate exception to real transition rules in this file,
//      clearly isolated to a single function.
//   3. **`is_archived` and outright deletion have zero backend basis** —
//      no archive/delete concept exists on the real aggregate at all,
//      matching this task's own "(UI)" qualifier on both features.
//
// `recipient_name`/`reference_label`/`quick_action_href` are denormalized
// display fields, same reasoning as every other mock repository in this
// app — `reference_type`/`reference_id` are real, open (non-enum) fields
// on the entity (see its own domain docstring for why), used here to
// link into other already-built modules' real detail pages.
//
// **Notification Settings has no backend basis whatsoever** — no
// preferences/channel entity exists anywhere in this codebase. Modeled
// entirely as a frontend invention below (`NotificationPreferences`),
// scoped to exactly what this task's "Notification Settings" section
// asks for.

import type { PaginatedResponse } from "@/types";

const MIN_LATENCY_MS = 350;

function mockFetch<T>(value: T, latencyMs: number = MIN_LATENCY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), latencyMs));
}

// --- Category (frontend taxonomy — see module docstring, point 1) -----

export type NotificationCategory =
  | "appointment"
  | "visit"
  | "clinical_note"
  | "soap_note"
  | "lab_report"
  | "prescription"
  | "medical_document"
  | "family_invitation"
  | "system"
  | "security";

export const NOTIFICATION_CATEGORY_OPTIONS: { label: string; value: NotificationCategory }[] = [
  { label: "Appointment", value: "appointment" },
  { label: "Visit", value: "visit" },
  { label: "Clinical Note", value: "clinical_note" },
  { label: "SOAP Note", value: "soap_note" },
  { label: "Lab Report", value: "lab_report" },
  { label: "Prescription", value: "prescription" },
  { label: "Medical Document", value: "medical_document" },
  { label: "Family Invitation", value: "family_invitation" },
  { label: "System", value: "system" },
  { label: "Security", value: "security" },
];

export function getNotificationCategoryLabel(category: NotificationCategory): string {
  return (
    NOTIFICATION_CATEGORY_OPTIONS.find((option) => option.value === category)?.label ?? category
  );
}

// The closest honest mapping of this file's 10-value UI taxonomy back
// onto the real 8-value `NotificationType` enum — `null` where no real
// member exists yet. Documentation only (nothing here calls a real API).
export type BackendNotificationType =
  | "appointment_reminder"
  | "appointment_confirmed"
  | "appointment_cancelled"
  | "visit_completed"
  | "prescription_ready"
  | "lab_result_ready"
  | "general"
  | "system";

export const CATEGORY_TO_BACKEND_TYPE: Record<
  NotificationCategory,
  BackendNotificationType | null
> = {
  appointment: "appointment_reminder",
  visit: "visit_completed",
  clinical_note: null,
  soap_note: null,
  lab_report: "lab_result_ready",
  prescription: "prescription_ready",
  medical_document: null,
  family_invitation: null,
  system: "system",
  security: null,
};

// --- Priority / status (verbatim from `app.modules.notification.domain.enums`) --

export type NotificationPriority = "low" | "normal" | "high" | "critical";

export const NOTIFICATION_PRIORITY_OPTIONS: { label: string; value: NotificationPriority }[] = [
  { label: "Low", value: "low" },
  { label: "Normal", value: "normal" },
  { label: "High", value: "high" },
  { label: "Critical", value: "critical" },
];

export function getNotificationPriorityLabel(priority: NotificationPriority): string {
  return (
    NOTIFICATION_PRIORITY_OPTIONS.find((option) => option.value === priority)?.label ?? priority
  );
}

const PRIORITY_RANK: Record<NotificationPriority, number> = {
  low: 0,
  normal: 1,
  high: 2,
  critical: 3,
};

export type NotificationStatus =
  "pending" | "scheduled" | "sent" | "delivered" | "read" | "cancelled" | "expired";

// A notification is "unread" once it's actually reached the recipient
// (`Delivered`) but hasn't been opened (`Read`) yet — the pre-delivery
// states (`Pending`/`Scheduled`/`Sent`) aren't something a user would see
// listed as an actionable inbox item.
export function isNotificationRead(status: NotificationStatus): boolean {
  return status === "read";
}

export function isNotificationUnread(status: NotificationStatus): boolean {
  return status === "delivered" || status === "sent";
}

// --- Core shape -----------------------------------------------------

export interface NotificationItem {
  notification_id: string;
  organization_id: string;
  recipient_user_id: string;
  recipient_name: string;
  category: NotificationCategory;
  title: string;
  message: string;
  priority: NotificationPriority;
  status: NotificationStatus;
  reference_type: string | null;
  reference_id: string | null;
  reference_label: string | null;
  quick_action_href: string | null;
  scheduled_at: string | null;
  sent_at: string | null;
  read_at: string | null;
  expires_at: string | null;
  is_archived: boolean;
  created_at: string; // ISO 8601
}

// --- In-memory seed data --------------------------------------------

const ORG_ID = "org-riverside-clinic";
const RECIPIENT_NAME = "Dr. Amara Okafor";

function hoursAgo(hours: number): string {
  return new Date(Date.now() - hours * 3_600_000).toISOString();
}

interface NotificationSeed {
  category: NotificationCategory;
  title: string;
  message: string;
  priority: NotificationPriority;
  status: NotificationStatus;
  reference_type: string | null;
  reference_id: string | null;
  reference_label: string | null;
  quick_action_href: string | null;
  createdHoursAgo: number;
  readHoursAgo: number | null;
  is_archived?: boolean;
}

const SEED: NotificationSeed[] = [
  {
    category: "appointment",
    title: "Upcoming appointment reminder",
    message: "You have an appointment with Michael Chen in 1 hour.",
    priority: "high",
    status: "delivered",
    reference_type: "appointment",
    reference_id: "apt-0001",
    reference_label: "Appointment APT-90001",
    quick_action_href: "/dashboard/appointments/apt-0001",
    createdHoursAgo: 1,
    readHoursAgo: null,
  },
  {
    category: "appointment",
    title: "Appointment confirmed",
    message: "Sarah Johnson confirmed her appointment for tomorrow at 9:00 AM.",
    priority: "normal",
    status: "read",
    reference_type: "appointment",
    reference_id: "apt-0002",
    reference_label: "Appointment APT-90002",
    quick_action_href: "/dashboard/appointments/apt-0002",
    createdHoursAgo: 20,
    readHoursAgo: 18,
  },
  {
    category: "visit",
    title: "Visit completed",
    message: "The visit for Amara Nwosu has been marked complete and is ready for review.",
    priority: "normal",
    status: "delivered",
    reference_type: "visit",
    reference_id: "vis8-0004",
    reference_label: "Visit VIS-80004",
    quick_action_href: "/dashboard/visits/vis8-0004",
    createdHoursAgo: 4,
    readHoursAgo: null,
  },
  {
    category: "clinical_note",
    title: "Clinical note awaiting signature",
    message: "A clinical note for David Kim is in review and needs your signature.",
    priority: "high",
    status: "delivered",
    reference_type: "clinical_note",
    reference_id: "cn-0003",
    reference_label: "Clinical Note CN-70003",
    quick_action_href: "/dashboard/clinical-notes/cn-0003",
    createdHoursAgo: 6,
    readHoursAgo: null,
  },
  {
    category: "soap_note",
    title: "SOAP note finalized",
    message: "A SOAP note for Sarah Johnson has been finalized.",
    priority: "low",
    status: "read",
    reference_type: "soap_note",
    reference_id: "soap-0002",
    reference_label: "SOAP Note",
    quick_action_href: "/dashboard/soap-notes/soap-0002",
    createdHoursAgo: 30,
    readHoursAgo: 28,
  },
  {
    category: "lab_report",
    title: "Lab results ready",
    message: "Lipid panel results for David Kim are ready for review.",
    priority: "critical",
    status: "delivered",
    reference_type: "lab_report",
    reference_id: "lab-0004",
    reference_label: "Lab Report LAB-60004",
    quick_action_href: "/dashboard/lab-reports/lab-0004",
    createdHoursAgo: 2,
    readHoursAgo: null,
  },
  {
    category: "lab_report",
    title: "Lab results ready",
    message: "Annual physical lab results for Michael Chen are ready for review.",
    priority: "normal",
    status: "read",
    reference_type: "lab_report",
    reference_id: "lab-0001",
    reference_label: "Lab Report LAB-60001",
    quick_action_href: "/dashboard/lab-reports/lab-0001",
    createdHoursAgo: 48,
    readHoursAgo: 40,
  },
  {
    category: "prescription",
    title: "Prescription ready",
    message: "A prescription for Sarah Johnson is ready for pickup.",
    priority: "normal",
    status: "delivered",
    reference_type: "prescription",
    reference_id: "presc-0002",
    reference_label: "Prescription",
    quick_action_href: "/dashboard/prescriptions/presc-0002",
    createdHoursAgo: 5,
    readHoursAgo: null,
  },
  {
    category: "medical_document",
    title: "New document uploaded",
    message: "Front Desk uploaded a new insurance card for Michael Chen.",
    priority: "low",
    status: "read",
    reference_type: "document",
    reference_id: "doc-0002",
    reference_label: "Insurance Card - Front and Back",
    quick_action_href: "/dashboard/documents/doc-0002",
    createdHoursAgo: 72,
    readHoursAgo: 70,
  },
  {
    category: "family_invitation",
    title: "Family invitation accepted",
    message: "Linda Chen accepted the invitation to access Michael Chen's record.",
    priority: "normal",
    status: "delivered",
    reference_type: "family_access",
    reference_id: "fam-0001",
    reference_label: "Linda Chen (Spouse)",
    quick_action_href: "/dashboard/family/fam-0001",
    createdHoursAgo: 10,
    readHoursAgo: null,
  },
  {
    category: "family_invitation",
    title: "Family invitation pending",
    message: "Kevin Chen has not yet responded to a family access invitation.",
    priority: "low",
    status: "read",
    reference_type: "family_access",
    reference_id: "fam-0002",
    reference_label: "Kevin Chen (Child)",
    quick_action_href: "/dashboard/family/fam-0002",
    createdHoursAgo: 60,
    readHoursAgo: 55,
  },
  {
    category: "system",
    title: "Scheduled maintenance",
    message: "DrAssist will undergo scheduled maintenance this Sunday from 2–4 AM.",
    priority: "low",
    status: "delivered",
    reference_type: null,
    reference_id: null,
    reference_label: null,
    quick_action_href: null,
    createdHoursAgo: 26,
    readHoursAgo: null,
  },
  {
    category: "system",
    title: "New feature: Health Timeline",
    message: "You can now view a patient's complete chronological health history.",
    priority: "low",
    status: "read",
    reference_type: null,
    reference_id: null,
    reference_label: null,
    quick_action_href: "/dashboard/timeline",
    createdHoursAgo: 96,
    readHoursAgo: 90,
    is_archived: true,
  },
  {
    category: "security",
    title: "New sign-in detected",
    message: "Your account was signed in from a new device in Austin, TX.",
    priority: "critical",
    status: "delivered",
    reference_type: null,
    reference_id: null,
    reference_label: null,
    quick_action_href: "/dashboard/settings",
    createdHoursAgo: 0.5,
    readHoursAgo: null,
  },
  {
    category: "security",
    title: "Password changed",
    message: "Your account password was changed successfully.",
    priority: "normal",
    status: "read",
    reference_type: null,
    reference_id: null,
    reference_label: null,
    quick_action_href: "/dashboard/settings",
    createdHoursAgo: 150,
    readHoursAgo: 148,
    is_archived: true,
  },
  {
    category: "appointment",
    title: "Appointment reminder scheduled",
    message: "A reminder for James Williams's appointment will be sent tomorrow morning.",
    priority: "low",
    status: "scheduled",
    reference_type: "appointment",
    reference_id: "apt-0005",
    reference_label: "Appointment APT-90005",
    quick_action_href: "/dashboard/appointments/apt-0005",
    createdHoursAgo: 3,
    readHoursAgo: null,
  },
];

let notifications: NotificationItem[] = SEED.map((seed, index) => {
  const num = index + 1;
  const notification_id = `notif-${String(num).padStart(4, "0")}`;
  const createdAt = hoursAgo(seed.createdHoursAgo);
  const readAt = seed.readHoursAgo === null ? null : hoursAgo(seed.readHoursAgo);
  const sentAt = seed.status === "scheduled" || seed.status === "pending" ? null : createdAt;
  const scheduledAt =
    seed.status === "scheduled" ? hoursAgo(Math.max(seed.createdHoursAgo - 20, 0)) : null;

  return {
    notification_id,
    organization_id: ORG_ID,
    recipient_user_id: "user-current",
    recipient_name: RECIPIENT_NAME,
    category: seed.category,
    title: seed.title,
    message: seed.message,
    priority: seed.priority,
    status: seed.status,
    reference_type: seed.reference_type,
    reference_id: seed.reference_id,
    reference_label: seed.reference_label,
    quick_action_href: seed.quick_action_href,
    scheduled_at: scheduledAt,
    sent_at: sentAt,
    read_at: readAt,
    expires_at: null,
    is_archived: Boolean(seed.is_archived),
    created_at: createdAt,
  };
});

// --- Repository: reads -----------------------------------------------

export interface NotificationListParams {
  search?: string;
  category?: NotificationCategory | "all";
  priority?: NotificationPriority | "all";
  readStatus?: "all" | "unread" | "read";
  includeArchived?: boolean;
  sortBy?: "created_at" | "priority" | "category" | "title";
  sortDirection?: "asc" | "desc";
  page?: number;
  pageSize?: number;
}

function matchesSearch(notification: NotificationItem, search: string): boolean {
  const needle = search.trim().toLowerCase();
  if (!needle) return true;
  return (
    notification.title.toLowerCase().includes(needle) ||
    notification.message.toLowerCase().includes(needle) ||
    (notification.reference_label?.toLowerCase().includes(needle) ?? false)
  );
}

function sortValue(
  notification: NotificationItem,
  sortBy: NonNullable<NotificationListParams["sortBy"]>,
): string | number {
  if (sortBy === "priority") return PRIORITY_RANK[notification.priority];
  return notification[sortBy];
}

export function listNotifications(
  params: NotificationListParams = {},
): Promise<PaginatedResponse<NotificationItem>> {
  const {
    search = "",
    category = "all",
    priority = "all",
    readStatus = "all",
    includeArchived = false,
    sortBy = "created_at",
    sortDirection = "desc",
    page = 1,
    pageSize = 10,
  } = params;

  let filtered = notifications.filter((notification) => matchesSearch(notification, search));
  if (!includeArchived) filtered = filtered.filter((notification) => !notification.is_archived);
  if (category !== "all")
    filtered = filtered.filter((notification) => notification.category === category);
  if (priority !== "all")
    filtered = filtered.filter((notification) => notification.priority === priority);
  if (readStatus === "unread") {
    filtered = filtered.filter((notification) => isNotificationUnread(notification.status));
  } else if (readStatus === "read") {
    filtered = filtered.filter((notification) => isNotificationRead(notification.status));
  }

  const sorted = [...filtered].sort((a, b) => {
    const left = sortValue(a, sortBy);
    const right = sortValue(b, sortBy);
    const comparison =
      typeof left === "number" && typeof right === "number"
        ? left - right
        : String(left).localeCompare(String(right));
    return sortDirection === "asc" ? comparison : -comparison;
  });

  const offset = (page - 1) * pageSize;
  const items = sorted.slice(offset, offset + pageSize);

  return mockFetch({
    items,
    total: sorted.length,
    offset,
    limit: pageSize,
    page,
    page_size: pageSize,
  });
}

export function getNotification(notificationId: string): Promise<NotificationItem | null> {
  const found =
    notifications.find((notification) => notification.notification_id === notificationId) ?? null;
  return mockFetch(found, 200);
}

// --- Repository: writes -------------------------------------------------

function updateNotification(
  notificationId: string,
  patch: Partial<NotificationItem>,
): NotificationItem {
  const index = notifications.findIndex(
    (notification) => notification.notification_id === notificationId,
  );
  const existing = notifications[index];
  if (!existing) throw new Error(`Notification ${notificationId} not found`);

  const updated: NotificationItem = { ...existing, ...patch };
  notifications = [...notifications.slice(0, index), updated, ...notifications.slice(index + 1)];
  return updated;
}

// Mirrors the real `mark_read()` transition (`Delivered -> Read`) —
// idempotent here (calling it on an already-read notification is a
// no-op rather than an error), since a UI "mark as read" action should
// never fail just because it was already read.
export async function markNotificationAsRead(notificationId: string): Promise<NotificationItem> {
  const notification = notifications.find((item) => item.notification_id === notificationId);
  if (!notification) throw new Error(`Notification ${notificationId} not found`);
  if (isNotificationRead(notification.status)) return mockFetch(notification, 200);

  const updated = updateNotification(notificationId, {
    status: "read",
    read_at: new Date().toISOString(),
  });
  return mockFetch(updated, 300);
}

// No real backend counterpart — see this file's own docstring, point 2.
export async function markNotificationAsUnread(notificationId: string): Promise<NotificationItem> {
  const notification = notifications.find((item) => item.notification_id === notificationId);
  if (!notification) throw new Error(`Notification ${notificationId} not found`);
  if (!isNotificationRead(notification.status)) return mockFetch(notification, 200);

  const updated = updateNotification(notificationId, { status: "delivered", read_at: null });
  return mockFetch(updated, 300);
}

// No real bulk-transition use case exists — this loops the same
// single-item `mark_read()` semantics client-side, matching what a real
// "mark all as read" endpoint would most plausibly do server-side too.
export async function markAllNotificationsAsRead(): Promise<number> {
  const now = new Date().toISOString();
  let count = 0;
  notifications = notifications.map((notification) => {
    if (!isNotificationUnread(notification.status)) return notification;
    count += 1;
    return { ...notification, status: "read" as const, read_at: now };
  });
  return mockFetch(count, 400);
}

// "(UI)" per this task's own Features list — see this file's own
// docstring, point 3.
export async function archiveNotification(notificationId: string): Promise<NotificationItem> {
  const updated = updateNotification(notificationId, { is_archived: true });
  return mockFetch(updated, 300);
}

export async function deleteNotification(notificationId: string): Promise<void> {
  notifications = notifications.filter(
    (notification) => notification.notification_id !== notificationId,
  );
  return mockFetch(undefined, 300);
}

// --- Grouping (pure, synchronous — see `lib/mock/timeline.ts` for the same pattern) --

export interface NotificationDateGroupData {
  dateKey: string; // "YYYY-MM-DD"
  notifications: NotificationItem[];
}

// Assumes `items` is already sorted newest-first.
export function groupNotificationsByDate(items: NotificationItem[]): NotificationDateGroupData[] {
  const groups = new Map<string, NotificationItem[]>();
  for (const notification of items) {
    const key = notification.created_at.slice(0, 10);
    const bucket = groups.get(key);
    if (bucket) {
      bucket.push(notification);
    } else {
      groups.set(key, [notification]);
    }
  }
  return Array.from(groups.entries()).map(([dateKey, dateNotifications]) => ({
    dateKey,
    notifications: dateNotifications,
  }));
}

// --- Notification Settings (entirely frontend-only — see module docstring) --

export type NotificationFrequency = "immediately" | "hourly_digest" | "daily_digest";

export const NOTIFICATION_FREQUENCY_OPTIONS: { label: string; value: NotificationFrequency }[] = [
  { label: "Immediately", value: "immediately" },
  { label: "Hourly Digest", value: "hourly_digest" },
  { label: "Daily Digest", value: "daily_digest" },
];

export function getNotificationFrequencyLabel(frequency: NotificationFrequency): string {
  return (
    NOTIFICATION_FREQUENCY_OPTIONS.find((option) => option.value === frequency)?.label ?? frequency
  );
}

export interface ChannelPreference {
  enabled: boolean;
  frequency: NotificationFrequency;
}

export interface NotificationPreferences {
  channels: {
    in_app: ChannelPreference;
    email: ChannelPreference;
    sms: ChannelPreference;
    push: ChannelPreference;
  };
  quiet_hours_enabled: boolean;
  quiet_hours_start: string; // "HH:mm"
  quiet_hours_end: string; // "HH:mm"
  emergency_override: boolean;
}

let preferences: NotificationPreferences = {
  channels: {
    in_app: { enabled: true, frequency: "immediately" },
    email: { enabled: true, frequency: "daily_digest" },
    sms: { enabled: false, frequency: "immediately" },
    push: { enabled: false, frequency: "immediately" },
  },
  quiet_hours_enabled: true,
  quiet_hours_start: "22:00",
  quiet_hours_end: "07:00",
  emergency_override: true,
};

export function getNotificationPreferences(): Promise<NotificationPreferences> {
  return mockFetch(preferences, 300);
}

export function updateNotificationPreferences(
  next: NotificationPreferences,
): Promise<NotificationPreferences> {
  preferences = next;
  return mockFetch(preferences, 500);
}
