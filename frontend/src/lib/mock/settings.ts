// Temporary frontend mock repository for Account, Security, and
// Preferences settings (`/dashboard/settings/*`). No backend API is
// consumed anywhere in this module.
//
// **Account Settings** is grounded in the real
// `app.modules.authentication.domain.entities.User` aggregate:
// `first_name`, `last_name`, `email`, `phone`, `locale`, `timezone` are
// all real fields, copied verbatim (including `locale`'s real default,
// `"en-US"`).
//
// **Security Settings** is grounded in three real entities:
//   - `mfa_enabled` — `User.mfa_enabled` verbatim. "Two-Factor
//     Authentication (UI)" here is a toggle over this real field; the
//     actual TOTP enrollment flow (QR code, backup codes, verification)
//     has no real use case built yet, matching the task's own "(UI)"
//     qualifier.
//   - Active Sessions / Login History — both views over the same real
//     `app.modules.authentication.domain.entities.UserSession` entity
//     (`device_label`, `ip_address`, `user_agent`, `issued_at`,
//     `last_used_at`, `expires_at`, `revoked_at`, `revoked_reason`).
//     "Active Sessions" = sessions with `revoked_at` null and not yet
//     expired; "Login History" = every session ever issued, most recent
//     first — the same underlying rows, two different filters, not two
//     different entities.
//   - `location`/`is_trusted`/`is_current_session` on `UserSessionItem`
//     have no real backend basis — geolocating an IP and "trusting" a
//     device are both invented for this task's own "Trusted Devices"/
//     display requirements, called out explicitly since nothing else in
//     this file is invented this freely.
//   - "Change Password (UI)" has no real backend counterpart modeled
//     here at all (no password-hash comparison is meaningful against
//     mock data) — `changePassword()` only validates that the two new
//     fields match, matching the task's own "(UI)" qualifier.
//
// **Preferences** (date format, time format, dashboard layout, default
// landing page) has *no* real backend basis whatsoever — entirely a
// frontend invention scoped to this task's own "Preferences" section.
// Theme is deliberately NOT modeled here: it's already real, working
// infrastructure (`next-themes`, see `components/layout/theme-toggle.tsx`),
// so `ThemeSelector` reads/writes it directly via `useTheme()` instead of
// going through this mock file.

const MIN_LATENCY_MS = 300;

function mockFetch<T>(value: T, latencyMs: number = MIN_LATENCY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), latencyMs));
}

// --- Account Settings (grounded in `User`) -----------------------------

export const LANGUAGE_OPTIONS: { label: string; value: string }[] = [
  { label: "English (US)", value: "en-US" },
  { label: "English (UK)", value: "en-GB" },
  { label: "Spanish", value: "es" },
  { label: "French", value: "fr" },
  { label: "German", value: "de" },
  { label: "Portuguese", value: "pt" },
  { label: "Mandarin Chinese", value: "zh" },
  { label: "Arabic", value: "ar" },
  { label: "Hindi", value: "hi" },
];

export function getLanguageLabel(locale: string): string {
  return LANGUAGE_OPTIONS.find((option) => option.value === locale)?.label ?? locale;
}

export const TIMEZONE_OPTIONS: { label: string; value: string }[] = [
  { label: "Eastern Time (US)", value: "America/New_York" },
  { label: "Central Time (US)", value: "America/Chicago" },
  { label: "Mountain Time (US)", value: "America/Denver" },
  { label: "Pacific Time (US)", value: "America/Los_Angeles" },
  { label: "Alaska Time", value: "America/Anchorage" },
  { label: "Hawaii Time", value: "Pacific/Honolulu" },
  { label: "Coordinated Universal Time", value: "UTC" },
  { label: "London", value: "Europe/London" },
  { label: "Paris", value: "Europe/Paris" },
  { label: "Mumbai / New Delhi", value: "Asia/Kolkata" },
  { label: "Tokyo", value: "Asia/Tokyo" },
  { label: "Sydney", value: "Australia/Sydney" },
];

export function getTimezoneLabel(timezone: string): string {
  return TIMEZONE_OPTIONS.find((option) => option.value === timezone)?.label ?? timezone;
}

export interface AccountSettings {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  locale: string;
  timezone: string;
}

let accountSettings: AccountSettings = {
  first_name: "Amara",
  last_name: "Okafor",
  email: "amara.okafor@riversideclinic.example",
  phone: "+1 (555) 010-2244",
  locale: "en-US",
  timezone: "America/Chicago",
};

export function getAccountSettings(): Promise<AccountSettings> {
  return mockFetch(accountSettings);
}

export function updateAccountSettings(input: AccountSettings): Promise<AccountSettings> {
  accountSettings = { ...input };
  return mockFetch(accountSettings, 500);
}

// --- Security Settings (grounded in `User.mfa_enabled` + `UserSession`) --

export interface SecurityOverview {
  mfa_enabled: boolean;
  password_last_changed_at: string | null;
}

let securityOverview: SecurityOverview = {
  mfa_enabled: false,
  password_last_changed_at: "2026-05-12T09:00:00.000Z",
};

export function getSecurityOverview(): Promise<SecurityOverview> {
  return mockFetch(securityOverview);
}

export function setTwoFactorEnabled(enabled: boolean): Promise<SecurityOverview> {
  securityOverview = { ...securityOverview, mfa_enabled: enabled };
  return mockFetch(securityOverview, 500);
}

export interface ChangePasswordInput {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

// "(UI)" per this task — see this file's own docstring. Only validates
// the two new-password fields match; there's no real password hash to
// compare `current_password` against.
export async function changePassword(input: ChangePasswordInput): Promise<{ success: true }> {
  if (input.new_password !== input.confirm_password) {
    throw new Error("New password and confirmation do not match.");
  }
  securityOverview = { ...securityOverview, password_last_changed_at: new Date().toISOString() };
  return mockFetch({ success: true }, 600);
}

export interface UserSessionItem {
  session_id: string;
  device_label: string;
  ip_address: string;
  user_agent: string;
  location: string;
  issued_at: string; // ISO 8601
  last_used_at: string | null;
  expires_at: string;
  revoked_at: string | null;
  revoked_reason: string | null;
  is_current_session: boolean;
  is_trusted: boolean;
}

function hoursAgo(hours: number): string {
  return new Date(Date.now() - hours * 3_600_000).toISOString();
}

function hoursFromNow(hours: number): string {
  return new Date(Date.now() + hours * 3_600_000).toISOString();
}

let sessions: UserSessionItem[] = [
  {
    session_id: "sess-0001",
    device_label: "Chrome on Windows",
    ip_address: "203.0.113.42",
    user_agent: "Chrome 124 · Windows 11",
    location: "Austin, TX, US",
    issued_at: hoursAgo(1),
    last_used_at: hoursAgo(0.1),
    expires_at: hoursFromNow(23),
    revoked_at: null,
    revoked_reason: null,
    is_current_session: true,
    is_trusted: true,
  },
  {
    session_id: "sess-0002",
    device_label: "Safari on iPhone",
    ip_address: "198.51.100.17",
    user_agent: "Safari 17 · iOS 17",
    location: "Austin, TX, US",
    issued_at: hoursAgo(20),
    last_used_at: hoursAgo(2),
    expires_at: hoursFromNow(4),
    revoked_at: null,
    revoked_reason: null,
    is_current_session: false,
    is_trusted: true,
  },
  {
    session_id: "sess-0003",
    device_label: "Chrome on macOS",
    ip_address: "192.0.2.88",
    user_agent: "Chrome 123 · macOS 14",
    location: "Dallas, TX, US",
    issued_at: hoursAgo(96),
    last_used_at: hoursAgo(90),
    expires_at: hoursAgo(72),
    revoked_at: null,
    revoked_reason: null,
    is_current_session: false,
    is_trusted: false,
  },
  {
    session_id: "sess-0004",
    device_label: "Firefox on Windows",
    ip_address: "203.0.113.9",
    user_agent: "Firefox 125 · Windows 10",
    location: "Unknown Location",
    issued_at: hoursAgo(200),
    last_used_at: hoursAgo(198),
    expires_at: hoursAgo(176),
    revoked_at: hoursAgo(180),
    revoked_reason: "Manually signed out",
    is_current_session: false,
    is_trusted: false,
  },
];

function isSessionActive(session: UserSessionItem): boolean {
  return session.revoked_at === null && new Date(session.expires_at).getTime() > Date.now();
}

export function listActiveSessions(): Promise<UserSessionItem[]> {
  return mockFetch(sessions.filter(isSessionActive));
}

// Every session ever issued, most recent first — see this file's own
// docstring for why this is the same underlying rows as Active Sessions.
export function listLoginHistory(): Promise<UserSessionItem[]> {
  const sorted = [...sessions].sort((a, b) => b.issued_at.localeCompare(a.issued_at));
  return mockFetch(sorted);
}

export function listTrustedDevices(): Promise<UserSessionItem[]> {
  return mockFetch(sessions.filter((session) => session.is_trusted));
}

export function revokeSession(sessionId: string): Promise<UserSessionItem> {
  const index = sessions.findIndex((session) => session.session_id === sessionId);
  const existing = sessions[index];
  if (!existing) throw new Error(`Session ${sessionId} not found`);

  const updated: UserSessionItem = {
    ...existing,
    revoked_at: new Date().toISOString(),
    revoked_reason: "Revoked by user",
  };
  sessions = [...sessions.slice(0, index), updated, ...sessions.slice(index + 1)];
  return mockFetch(updated, 400);
}

export function setSessionTrusted(sessionId: string, trusted: boolean): Promise<UserSessionItem> {
  const index = sessions.findIndex((session) => session.session_id === sessionId);
  const existing = sessions[index];
  if (!existing) throw new Error(`Session ${sessionId} not found`);

  const updated: UserSessionItem = { ...existing, is_trusted: trusted };
  sessions = [...sessions.slice(0, index), updated, ...sessions.slice(index + 1)];
  return mockFetch(updated, 300);
}

// --- Preferences (entirely frontend-only — see module docstring) -------

export type DateFormat = "MM/DD/YYYY" | "DD/MM/YYYY" | "YYYY-MM-DD";

export const DATE_FORMAT_OPTIONS: { label: string; value: DateFormat }[] = [
  { label: "MM/DD/YYYY", value: "MM/DD/YYYY" },
  { label: "DD/MM/YYYY", value: "DD/MM/YYYY" },
  { label: "YYYY-MM-DD", value: "YYYY-MM-DD" },
];

export type TimeFormatPreference = "12h" | "24h";

export const TIME_FORMAT_OPTIONS: { label: string; value: TimeFormatPreference }[] = [
  { label: "12-hour (2:30 PM)", value: "12h" },
  { label: "24-hour (14:30)", value: "24h" },
];

export type DashboardLayoutPreference = "comfortable" | "compact";

export const DASHBOARD_LAYOUT_OPTIONS: { label: string; value: DashboardLayoutPreference }[] = [
  { label: "Comfortable", value: "comfortable" },
  { label: "Compact", value: "compact" },
];

export type DefaultLandingPage =
  | "/dashboard"
  | "/dashboard/patients"
  | "/dashboard/appointments"
  | "/dashboard/timeline"
  | "/dashboard/notifications";

export const DEFAULT_LANDING_PAGE_OPTIONS: { label: string; value: DefaultLandingPage }[] = [
  { label: "Dashboard Overview", value: "/dashboard" },
  { label: "Patients", value: "/dashboard/patients" },
  { label: "Appointments", value: "/dashboard/appointments" },
  { label: "Health Timeline", value: "/dashboard/timeline" },
  { label: "Notifications", value: "/dashboard/notifications" },
];

export interface UserPreferences {
  date_format: DateFormat;
  time_format: TimeFormatPreference;
  dashboard_layout: DashboardLayoutPreference;
  default_landing_page: DefaultLandingPage;
}

let userPreferences: UserPreferences = {
  date_format: "MM/DD/YYYY",
  time_format: "12h",
  dashboard_layout: "comfortable",
  default_landing_page: "/dashboard",
};

export function getUserPreferences(): Promise<UserPreferences> {
  return mockFetch(userPreferences);
}

export function updateUserPreferences(input: UserPreferences): Promise<UserPreferences> {
  userPreferences = { ...input };
  return mockFetch(userPreferences, 500);
}
