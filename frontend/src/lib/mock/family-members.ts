// Temporary frontend mock repository for Family / Caregiver Access
// (`app/(dashboard)/dashboard/family/*`). No backend API is consumed
// anywhere in this module — every function below reads from and writes
// to an in-memory array, standing in for the real backend
// `app.modules.family_access` module (aggregate `FamilyAccess`) until
// its REST endpoints are wired up here.
//
// Field names are grounded in the real domain entity
// (`app.modules.family_access.domain.entities.FamilyAccess`) and its
// wire schema (`api/schemas.py::FamilyAccessResponse`): `organization_id,
// patient_id, caregiver_user_id, relationship, access_level, status,
// invitation_expires_at, accepted_at, revoked_at, notes`.
// `Relationship`/`FamilyAccessStatus` match `domain/enums.py` verbatim
// (9 and 5 values respectively). `status` follows the real entity's
// exact branching transition graph — `Pending` fans out to
// `Accepted`/`Rejected`/`Revoked`/`Expired`, and only `Accepted` has a
// further edge (`-> Revoked`) — never a linear chain.
//
// Three deliberate departures from the real backend, each called out
// because nothing forced this shape but the task's own requirements:
//
//   1. **`AccessLevel` here is a 4-tier UI taxonomy
//      (`viewer/caregiver/emergency_contact/guardian`), not the real
//      backend's 3-value enum** (`read_only/limited_medical/
//      full_medical`). The task's own "Access Levels" section asks for
//      exactly these four named tiers plus a "Custom Permissions" mode —
//      a healthcare-appropriate synthesis of the real `AccessLevel` *and*
//      `Relationship` enums (the backend's `Relationship` enum already
//      has `guardian`/`caregiver` as relationship types, not access
//      tiers). `toBackendAccessLevel()` below documents the closest
//      honest collapse back to the real 3-value enum, for when this
//      becomes backend-API-ready.
//   2. **`FamilyMemberPermissions` (10 booleans) has no backend
//      equivalent at all** — the real entity is governed solely by its
//      coarse `access_level`, no permission bitmask/list field exists.
//      This is invented entirely for the task's "Permissions UI"/
//      `PermissionMatrix`/`PermissionToggleGroup` requirement.
//      `getDefaultPermissions()` derives a sensible default set per
//      access tier; `has_custom_permissions` records whether a grant's
//      permissions were left at that default or edited individually.
//   3. **The real `InviteCaregiver` use case requires an existing
//      `caregiver_user_id`**, resolved server-side via the Authentication
//      module's `UserQueryPort` (`CaregiverNotFoundError` if the invitee
//      isn't already a platform `User`). This app has no general "browse
//      platform users" module built yet (`/dashboard/access-control` is
//      still an unbuilt nav placeholder), so this mock's invitation form
//      collects the caregiver's name/email/phone directly instead of a
//      picker, and `createFamilyAccessGrant()` synthesizes a
//      `caregiver_user_id`. Swapping in a real user picker is a drop-in
//      follow-up once a Users module exists.
//
// `member_name`/`email`/`phone`/`patient_name`/`patient_number`/
// `invited_by_name` are denormalized display fields, same reasoning as
// every other mock repository in this app. `history`
// (`FamilyAccessHistoryEntry[]`) mirrors the same invented-status-log
// pattern already established for `AppointmentStatusHistoryEntry`/
// `VisitTimelineEvent` — the real backend fires one domain event per
// transition, no queryable log. `recent_activity` has zero backend
// basis at all (no access-log entity exists yet); seeded only for
// accepted members, purely for the task's "Recent Activity" section.
//
// `invitation_token` (a SHA-256 hash on the real entity, never the raw
// value after creation) is deliberately not modeled — nothing in this
// module's UI displays it; the real backend returns the raw token to the
// inviter exactly once, at invite time, which this mock doesn't need to
// simulate since no email-sending flow exists here.

import type { PaginatedResponse } from "@/types";

const MIN_LATENCY_MS = 350;

function mockFetch<T>(value: T, latencyMs: number = MIN_LATENCY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), latencyMs));
}

function generateId(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

// Mirrors `application/constants.py::INVITATION_EXPIRY_DAYS` verbatim.
const INVITATION_EXPIRY_DAYS = 7;

// --- Enums (verbatim from `app.modules.family_access.domain.enums`) --

export type Relationship =
  | "parent"
  | "child"
  | "spouse"
  | "sibling"
  | "guardian"
  | "caregiver"
  | "relative"
  | "friend"
  | "other";

export const RELATIONSHIP_OPTIONS: { label: string; value: Relationship }[] = [
  { label: "Parent", value: "parent" },
  { label: "Child", value: "child" },
  { label: "Spouse", value: "spouse" },
  { label: "Sibling", value: "sibling" },
  { label: "Guardian", value: "guardian" },
  { label: "Caregiver", value: "caregiver" },
  { label: "Relative", value: "relative" },
  { label: "Friend", value: "friend" },
  { label: "Other", value: "other" },
];

export function getRelationshipLabel(relationship: Relationship): string {
  return (
    RELATIONSHIP_OPTIONS.find((option) => option.value === relationship)?.label ?? relationship
  );
}

export type FamilyAccessStatus = "pending" | "accepted" | "rejected" | "revoked" | "expired";

// "Declined" (not "Rejected") per this task's own explicit "Declined
// Status" wording, even though the real domain enum member is
// `REJECTED` — display label only, the underlying value is unchanged.
export const FAMILY_ACCESS_STATUS_OPTIONS: { label: string; value: FamilyAccessStatus }[] = [
  { label: "Pending", value: "pending" },
  { label: "Accepted", value: "accepted" },
  { label: "Declined", value: "rejected" },
  { label: "Revoked", value: "revoked" },
  { label: "Expired", value: "expired" },
];

export function getFamilyAccessStatusLabel(status: FamilyAccessStatus): string {
  return FAMILY_ACCESS_STATUS_OPTIONS.find((option) => option.value === status)?.label ?? status;
}

// Mirrors `FamilyAccess._ALLOWED_TRANSITIONS` exactly: only Pending or
// Accepted can move to Revoked; every other status is terminal.
export function isFamilyAccessRevocable(status: FamilyAccessStatus): boolean {
  return status === "pending" || status === "accepted";
}

// A pending invitation can be cancelled (revoked before it's ever
// accepted) or resent (its expiry extended) — both only while Pending.
export function isFamilyAccessCancellable(status: FamilyAccessStatus): boolean {
  return status === "pending";
}

// --- Access levels (frontend UI taxonomy — see module docstring) ------

export type AccessLevel = "viewer" | "caregiver" | "emergency_contact" | "guardian";

export const ACCESS_LEVEL_OPTIONS: { label: string; value: AccessLevel }[] = [
  { label: "Viewer", value: "viewer" },
  { label: "Caregiver", value: "caregiver" },
  { label: "Emergency Contact", value: "emergency_contact" },
  { label: "Guardian", value: "guardian" },
];

export function getAccessLevelLabel(accessLevel: AccessLevel): string {
  return ACCESS_LEVEL_OPTIONS.find((option) => option.value === accessLevel)?.label ?? accessLevel;
}

const ACCESS_LEVEL_DESCRIPTIONS: Record<AccessLevel, string> = {
  viewer: "Can view basic profile, appointments, and visit history only.",
  caregiver: "Day-to-day involvement in care: clinical notes, labs, prescriptions, and documents.",
  emergency_contact:
    "Critical-info-only access for emergencies: profile, current medications, and labs.",
  guardian: "Full access on the patient's behalf, including downloading documents.",
};

export function getAccessLevelDescription(accessLevel: AccessLevel): string {
  return ACCESS_LEVEL_DESCRIPTIONS[accessLevel];
}

// The closest honest collapse of this module's 4-tier UI taxonomy back
// onto the real backend's 3-value `AccessLevel` enum — see this file's
// own docstring, point 1. Not called anywhere yet (nothing here talks to
// a real API), kept as documentation of the intended mapping.
export type BackendAccessLevel = "read_only" | "limited_medical" | "full_medical";

export function toBackendAccessLevel(accessLevel: AccessLevel): BackendAccessLevel {
  switch (accessLevel) {
    case "viewer":
      return "read_only";
    case "emergency_contact":
      return "limited_medical";
    case "caregiver":
      return "limited_medical";
    case "guardian":
      return "full_medical";
  }
}

// --- Permissions (frontend-only invention — see module docstring) -----

export interface FamilyMemberPermissions {
  patient_profile: boolean;
  appointments: boolean;
  visits: boolean;
  clinical_notes: boolean;
  soap_notes: boolean;
  lab_reports: boolean;
  prescriptions: boolean;
  medical_documents: boolean;
  health_timeline: boolean;
  download_documents: boolean;
}

export const PERMISSION_FIELDS: { key: keyof FamilyMemberPermissions; label: string }[] = [
  { key: "patient_profile", label: "Patient Profile" },
  { key: "appointments", label: "Appointments" },
  { key: "visits", label: "Visits" },
  { key: "clinical_notes", label: "Clinical Notes" },
  { key: "soap_notes", label: "SOAP Notes" },
  { key: "lab_reports", label: "Lab Reports" },
  { key: "prescriptions", label: "Prescriptions" },
  { key: "medical_documents", label: "Medical Documents" },
  { key: "health_timeline", label: "Health Timeline" },
  { key: "download_documents", label: "Download Documents" },
];

const DEFAULT_PERMISSIONS_BY_ACCESS_LEVEL: Record<AccessLevel, FamilyMemberPermissions> = {
  viewer: {
    patient_profile: true,
    appointments: true,
    visits: true,
    clinical_notes: false,
    soap_notes: false,
    lab_reports: false,
    prescriptions: false,
    medical_documents: false,
    health_timeline: true,
    download_documents: false,
  },
  emergency_contact: {
    patient_profile: true,
    appointments: false,
    visits: false,
    clinical_notes: false,
    soap_notes: false,
    lab_reports: true,
    prescriptions: true,
    medical_documents: false,
    health_timeline: true,
    download_documents: false,
  },
  caregiver: {
    patient_profile: true,
    appointments: true,
    visits: true,
    clinical_notes: true,
    soap_notes: false,
    lab_reports: true,
    prescriptions: true,
    medical_documents: true,
    health_timeline: true,
    download_documents: false,
  },
  guardian: {
    patient_profile: true,
    appointments: true,
    visits: true,
    clinical_notes: true,
    soap_notes: true,
    lab_reports: true,
    prescriptions: true,
    medical_documents: true,
    health_timeline: true,
    download_documents: true,
  },
};

export function getDefaultPermissions(accessLevel: AccessLevel): FamilyMemberPermissions {
  return { ...DEFAULT_PERMISSIONS_BY_ACCESS_LEVEL[accessLevel] };
}

// --- Core shapes ---------------------------------------------------------

export interface FamilyAccessHistoryEntry {
  status: FamilyAccessStatus;
  changed_at: string; // ISO 8601
  note: string | null;
}

export interface FamilyActivityEntry {
  activity_id: string;
  description: string;
  occurred_at: string; // ISO 8601
}

export interface FamilyMember {
  family_access_id: string;
  organization_id: string;
  patient_id: string;
  patient_name: string;
  patient_number: string;
  caregiver_user_id: string;
  member_name: string;
  email: string;
  phone: string;
  relationship: Relationship;
  access_level: AccessLevel;
  status: FamilyAccessStatus;
  invited_at: string; // ISO 8601
  invitation_expires_at: string; // ISO 8601
  accepted_at: string | null;
  revoked_at: string | null;
  last_activity_at: string | null;
}

export interface FamilyMemberDetail extends FamilyMember {
  has_custom_permissions: boolean;
  permissions: FamilyMemberPermissions;
  notes: string | null;
  invited_by_name: string;
  history: FamilyAccessHistoryEntry[];
  recent_activity: FamilyActivityEntry[];
}

// --- In-memory seed data --------------------------------------------

const ORG_ID = "org-riverside-clinic";

function dateOffset(days: number): string {
  const value = new Date();
  value.setDate(value.getDate() + days);
  return value.toISOString().slice(0, 10);
}

function atTime(isoDate: string, time: string): Date {
  return new Date(`${isoDate}T${time}:00`);
}

function buildHistory(
  status: FamilyAccessStatus,
  invitedAt: Date,
  resolvedAt: Date | null,
): FamilyAccessHistoryEntry[] {
  const history: FamilyAccessHistoryEntry[] = [
    { status: "pending", changed_at: invitedAt.toISOString(), note: "Invitation sent." },
  ];
  if (status === "pending") return history;

  const resolution = resolvedAt ?? invitedAt;
  if (status === "accepted") {
    history.push({
      status: "accepted",
      changed_at: resolution.toISOString(),
      note: "Invitation accepted.",
    });
  } else if (status === "rejected") {
    history.push({
      status: "rejected",
      changed_at: resolution.toISOString(),
      note: "Invitation declined.",
    });
  } else if (status === "expired") {
    history.push({
      status: "expired",
      changed_at: resolution.toISOString(),
      note: "Invitation expired unused.",
    });
  } else if (status === "revoked") {
    history.push({
      status: "accepted",
      changed_at: invitedAt.toISOString(),
      note: "Invitation accepted.",
    });
    history.push({
      status: "revoked",
      changed_at: resolution.toISOString(),
      note: "Access revoked.",
    });
  }
  return history;
}

function buildActivity(
  memberName: string,
  permissions: FamilyMemberPermissions,
  baseDate: Date,
): FamilyActivityEntry[] {
  const activity: FamilyActivityEntry[] = [
    {
      activity_id: generateId("act"),
      description: `${memberName} viewed the patient profile.`,
      occurred_at: new Date(baseDate.getTime() - 2 * 86_400_000).toISOString(),
    },
  ];
  if (permissions.appointments) {
    activity.push({
      activity_id: generateId("act"),
      description: `${memberName} viewed upcoming appointments.`,
      occurred_at: new Date(baseDate.getTime() - 1 * 86_400_000).toISOString(),
    });
  }
  if (permissions.download_documents) {
    activity.push({
      activity_id: generateId("act"),
      description: `${memberName} downloaded a medical document.`,
      occurred_at: baseDate.toISOString(),
    });
  }
  return activity;
}

interface FamilyMemberSeed {
  patient_id: string;
  patient_name: string;
  patient_number: string;
  member_name: string;
  email: string;
  phone: string;
  relationship: Relationship;
  access_level: AccessLevel;
  status: FamilyAccessStatus;
  has_custom_permissions?: boolean;
  invited_by_name: string;
  notes: string | null;
  invitedDaysAgo: number;
  resolvedDaysAgo: number | null;
}

const SEED: FamilyMemberSeed[] = [
  {
    patient_id: "pat-0001",
    patient_name: "Michael Chen",
    patient_number: "PAT-100001",
    member_name: "Linda Chen",
    email: "linda.chen@example.com",
    phone: "+1 (555) 201-3344",
    relationship: "spouse",
    access_level: "guardian",
    status: "accepted",
    invited_by_name: "Front Desk",
    notes: "Primary caregiver, manages all appointments.",
    invitedDaysAgo: 60,
    resolvedDaysAgo: 58,
  },
  {
    patient_id: "pat-0001",
    patient_name: "Michael Chen",
    patient_number: "PAT-100001",
    member_name: "Kevin Chen",
    email: "kevin.chen@example.com",
    phone: "+1 (555) 201-9981",
    relationship: "child",
    access_level: "viewer",
    status: "pending",
    invited_by_name: "Dr. Amara Okafor",
    notes: null,
    invitedDaysAgo: 3,
    resolvedDaysAgo: null,
  },
  {
    patient_id: "pat-0002",
    patient_name: "Sarah Johnson",
    patient_number: "PAT-100002",
    member_name: "Mark Johnson",
    email: "mark.johnson@example.com",
    phone: "+1 (555) 330-1120",
    relationship: "spouse",
    access_level: "caregiver",
    status: "accepted",
    invited_by_name: "Front Desk",
    notes: null,
    invitedDaysAgo: 40,
    resolvedDaysAgo: 39,
  },
  {
    patient_id: "pat-0003",
    patient_name: "Amara Nwosu",
    patient_number: "PAT-100003",
    member_name: "Chidi Nwosu",
    email: "chidi.nwosu@example.com",
    phone: "+1 (555) 440-2233",
    relationship: "sibling",
    access_level: "emergency_contact",
    status: "accepted",
    invited_by_name: "Dr. Amara Okafor",
    notes: "Lives nearby, first point of contact for emergencies.",
    invitedDaysAgo: 25,
    resolvedDaysAgo: 24,
  },
  {
    patient_id: "pat-0003",
    patient_name: "Amara Nwosu",
    patient_number: "PAT-100003",
    member_name: "Ngozi Eze",
    email: "ngozi.eze@example.com",
    phone: "+1 (555) 440-7765",
    relationship: "relative",
    access_level: "viewer",
    status: "rejected",
    invited_by_name: "Front Desk",
    notes: null,
    invitedDaysAgo: 15,
    resolvedDaysAgo: 14,
  },
  {
    patient_id: "pat-0004",
    patient_name: "David Kim",
    patient_number: "PAT-100004",
    member_name: "Grace Kim",
    email: "grace.kim@example.com",
    phone: "+1 (555) 552-8890",
    relationship: "parent",
    access_level: "guardian",
    status: "accepted",
    invited_by_name: "Dr. Daniel Reyes",
    notes: null,
    invitedDaysAgo: 90,
    resolvedDaysAgo: 89,
  },
  {
    patient_id: "pat-0004",
    patient_name: "David Kim",
    patient_number: "PAT-100004",
    member_name: "Alex Rivera",
    email: "alex.rivera@example.com",
    phone: "+1 (555) 552-4471",
    relationship: "friend",
    access_level: "viewer",
    status: "expired",
    invited_by_name: "Front Desk",
    notes: null,
    invitedDaysAgo: 20,
    resolvedDaysAgo: 13,
  },
  {
    patient_id: "pat-0006",
    patient_name: "James Williams",
    patient_number: "PAT-100006",
    member_name: "Patricia Williams",
    email: "patricia.williams@example.com",
    phone: "+1 (555) 667-3321",
    relationship: "spouse",
    access_level: "caregiver",
    status: "revoked",
    invited_by_name: "Dr. Marcus Webb",
    notes: "Access revoked at patient's request.",
    invitedDaysAgo: 120,
    resolvedDaysAgo: 10,
  },
  {
    patient_id: "pat-0011",
    patient_name: "Robert Lee",
    patient_number: "PAT-100011",
    member_name: "Susan Lee",
    email: "susan.lee@example.com",
    phone: "+1 (555) 778-6612",
    relationship: "child",
    access_level: "guardian",
    status: "pending",
    invited_by_name: "Dr. Marcus Webb",
    notes: null,
    invitedDaysAgo: 1,
    resolvedDaysAgo: null,
  },
  {
    patient_id: "pat-0013",
    patient_name: "Noah Thompson",
    patient_number: "PAT-100013",
    member_name: "Diane Thompson",
    email: "diane.thompson@example.com",
    phone: "+1 (555) 889-2210",
    relationship: "parent",
    access_level: "caregiver",
    status: "accepted",
    invited_by_name: "Front Desk",
    notes: null,
    invitedDaysAgo: 33,
    resolvedDaysAgo: 32,
  },
  {
    patient_id: "pat-0014",
    patient_name: "Ava Rodriguez",
    patient_number: "PAT-100014",
    member_name: "Carlos Rodriguez",
    email: "carlos.rodriguez@example.com",
    phone: "+1 (555) 991-4432",
    relationship: "spouse",
    access_level: "emergency_contact",
    status: "accepted",
    has_custom_permissions: true,
    invited_by_name: "Dr. Hannah Kim",
    notes: "Customized to also allow viewing medical documents.",
    invitedDaysAgo: 18,
    resolvedDaysAgo: 17,
  },
  {
    patient_id: "pat-0016",
    patient_name: "Sofia Torres",
    patient_number: "PAT-100016",
    member_name: "Elena Torres",
    email: "elena.torres@example.com",
    phone: "+1 (555) 112-5589",
    relationship: "guardian",
    access_level: "guardian",
    status: "accepted",
    invited_by_name: "Dr. Hannah Kim",
    notes: "Legal guardian.",
    invitedDaysAgo: 200,
    resolvedDaysAgo: 199,
  },
];

let familyMembers: FamilyMemberDetail[] = SEED.map((seed, index) => {
  const num = index + 1;
  const family_access_id = `fam-${String(num).padStart(4, "0")}`;
  const invitedAt = atTime(dateOffset(-seed.invitedDaysAgo), "10:00");
  const resolvedAt =
    seed.resolvedDaysAgo === null ? null : atTime(dateOffset(-seed.resolvedDaysAgo), "10:00");
  const invitationExpiresAt = new Date(invitedAt.getTime() + INVITATION_EXPIRY_DAYS * 86_400_000);

  let permissions = getDefaultPermissions(seed.access_level);
  if (seed.has_custom_permissions) {
    permissions = { ...permissions, medical_documents: true };
  }

  const acceptedAt = seed.status === "accepted" ? resolvedAt : null;
  const revokedAt = seed.status === "revoked" ? resolvedAt : null;
  const lastActivityAt = seed.status === "accepted" ? new Date().toISOString() : null;

  return {
    family_access_id,
    organization_id: ORG_ID,
    patient_id: seed.patient_id,
    patient_name: seed.patient_name,
    patient_number: seed.patient_number,
    caregiver_user_id: generateId("user"),
    member_name: seed.member_name,
    email: seed.email,
    phone: seed.phone,
    relationship: seed.relationship,
    access_level: seed.access_level,
    status: seed.status,
    invited_at: invitedAt.toISOString(),
    invitation_expires_at: invitationExpiresAt.toISOString(),
    accepted_at: acceptedAt?.toISOString() ?? null,
    revoked_at: revokedAt?.toISOString() ?? null,
    last_activity_at: lastActivityAt,
    has_custom_permissions: Boolean(seed.has_custom_permissions),
    permissions,
    notes: seed.notes,
    invited_by_name: seed.invited_by_name,
    history: buildHistory(seed.status, invitedAt, resolvedAt),
    recent_activity:
      seed.status === "accepted"
        ? buildActivity(seed.member_name, permissions, resolvedAt ?? invitedAt)
        : [],
  };
});

// --- Repository: reads -----------------------------------------------

export interface FamilyMemberListParams {
  search?: string;
  status?: FamilyAccessStatus | "all";
  accessLevel?: AccessLevel | "all";
  relationship?: Relationship | "all";
  sortBy?:
    "member_name" | "relationship" | "access_level" | "status" | "invited_at" | "last_activity_at";
  sortDirection?: "asc" | "desc";
  page?: number;
  pageSize?: number;
}

function matchesSearch(member: FamilyMember, search: string): boolean {
  const needle = search.trim().toLowerCase();
  if (!needle) return true;
  return (
    member.member_name.toLowerCase().includes(needle) ||
    member.email.toLowerCase().includes(needle) ||
    member.patient_name.toLowerCase().includes(needle) ||
    member.phone.toLowerCase().includes(needle)
  );
}

function sortKey(
  member: FamilyMember,
  sortBy: NonNullable<FamilyMemberListParams["sortBy"]>,
): string {
  return member[sortBy] ?? "";
}

function stripDetail(member: FamilyMemberDetail): FamilyMember {
  return {
    family_access_id: member.family_access_id,
    organization_id: member.organization_id,
    patient_id: member.patient_id,
    patient_name: member.patient_name,
    patient_number: member.patient_number,
    caregiver_user_id: member.caregiver_user_id,
    member_name: member.member_name,
    email: member.email,
    phone: member.phone,
    relationship: member.relationship,
    access_level: member.access_level,
    status: member.status,
    invited_at: member.invited_at,
    invitation_expires_at: member.invitation_expires_at,
    accepted_at: member.accepted_at,
    revoked_at: member.revoked_at,
    last_activity_at: member.last_activity_at,
  };
}

export function listFamilyMembers(
  params: FamilyMemberListParams = {},
): Promise<PaginatedResponse<FamilyMember>> {
  const {
    search = "",
    status = "all",
    accessLevel = "all",
    relationship = "all",
    sortBy = "invited_at",
    sortDirection = "desc",
    page = 1,
    pageSize = 10,
  } = params;

  let filtered = familyMembers.filter((member) => matchesSearch(member, search));
  if (status !== "all") filtered = filtered.filter((member) => member.status === status);
  if (accessLevel !== "all")
    filtered = filtered.filter((member) => member.access_level === accessLevel);
  if (relationship !== "all")
    filtered = filtered.filter((member) => member.relationship === relationship);

  const sorted = [...filtered].sort((a, b) => {
    const comparison = sortKey(a, sortBy).localeCompare(sortKey(b, sortBy));
    return sortDirection === "asc" ? comparison : -comparison;
  });

  const offset = (page - 1) * pageSize;
  const items = sorted.slice(offset, offset + pageSize).map(stripDetail);

  return mockFetch({
    items,
    total: sorted.length,
    offset,
    limit: pageSize,
    page,
    page_size: pageSize,
  });
}

export function getFamilyMember(familyAccessId: string): Promise<FamilyMemberDetail | null> {
  const found = familyMembers.find((member) => member.family_access_id === familyAccessId) ?? null;
  return mockFetch(found, 300);
}

// --- Repository: writes -------------------------------------------------
// `organization_id`/`caregiver_user_id`/`status`/`invitation_token` are
// deliberately absent from this input shape — all server-controlled on
// the real `POST /family-access` endpoint (`InviteCaregiverRequest`
// itself doesn't even accept `caregiver_user_id` as free text — it's a
// UUID resolved from a picker in a real client — see this file's own
// docstring, point 3, for why this mock collects contact fields instead).

export interface FamilyInviteInput {
  patient_id: string;
  member_name: string;
  email: string;
  phone: string;
  relationship: Relationship;
  access_level: AccessLevel;
  has_custom_permissions: boolean;
  permissions: FamilyMemberPermissions;
  notes: string;
}

function resolvePatientDisplay(patientId: string): { name: string; number: string } {
  const existing = familyMembers.find((member) => member.patient_id === patientId);
  return existing
    ? { name: existing.patient_name, number: existing.patient_number }
    : { name: "Unknown Patient", number: "—" };
}

// Mirrors `InviteCaregiver`'s own duplicate-active-grant guard
// (`DuplicateActiveAccessError`): the same patient can't have two
// live (pending or accepted) grants for the same caregiver email.
function hasActiveGrant(patientId: string, email: string): boolean {
  return familyMembers.some(
    (member) =>
      member.patient_id === patientId &&
      member.email.toLowerCase() === email.toLowerCase() &&
      (member.status === "pending" || member.status === "accepted"),
  );
}

export async function createFamilyAccessGrant(
  input: FamilyInviteInput,
): Promise<FamilyMemberDetail> {
  if (hasActiveGrant(input.patient_id, input.email)) {
    throw new Error("This person already has an active or pending invitation for this patient.");
  }

  const id = generateId("fam");
  const patient = resolvePatientDisplay(input.patient_id);
  const now = new Date();
  const invitationExpiresAt = new Date(now.getTime() + INVITATION_EXPIRY_DAYS * 86_400_000);

  const created: FamilyMemberDetail = {
    family_access_id: id,
    organization_id: ORG_ID,
    patient_id: input.patient_id,
    patient_name: patient.name,
    patient_number: patient.number,
    caregiver_user_id: generateId("user"),
    member_name: input.member_name,
    email: input.email,
    phone: input.phone,
    relationship: input.relationship,
    access_level: input.access_level,
    status: "pending",
    invited_at: now.toISOString(),
    invitation_expires_at: invitationExpiresAt.toISOString(),
    accepted_at: null,
    revoked_at: null,
    last_activity_at: null,
    has_custom_permissions: input.has_custom_permissions,
    permissions: input.permissions,
    notes: input.notes || null,
    invited_by_name: "You",
    history: [{ status: "pending", changed_at: now.toISOString(), note: "Invitation sent." }],
    recent_activity: [],
  };

  familyMembers = [created, ...familyMembers];
  return mockFetch(created, 600);
}

function findIndexOrThrow(familyAccessId: string): number {
  const index = familyMembers.findIndex((member) => member.family_access_id === familyAccessId);
  if (index === -1) throw new Error(`Family access grant ${familyAccessId} not found`);
  return index;
}

// Mirrors `RevokeAccess` exactly: `(Pending|Accepted) -> Revoked`,
// terminal, never restorable.
export async function revokeFamilyMember(familyAccessId: string): Promise<FamilyMemberDetail> {
  const index = findIndexOrThrow(familyAccessId);
  const existing = familyMembers[index];
  if (!existing) throw new Error(`Family access grant ${familyAccessId} not found`);
  if (!isFamilyAccessRevocable(existing.status)) {
    throw new Error(`Grant ${familyAccessId} cannot be revoked from status ${existing.status}`);
  }

  const now = new Date().toISOString();
  const updated: FamilyMemberDetail = {
    ...existing,
    status: "revoked",
    revoked_at: now,
    history: [...existing.history, { status: "revoked", changed_at: now, note: "Access revoked." }],
  };

  familyMembers = [...familyMembers.slice(0, index), updated, ...familyMembers.slice(index + 1)];
  return mockFetch(updated, 500);
}

// No real backend use case exists for this yet (see this file's own
// docstring) — the closest honest behavior is re-running the same
// expiry math `InviteCaregiver` already does, keeping the same grant
// and history rather than creating a new one.
export async function resendFamilyInvitation(familyAccessId: string): Promise<FamilyMemberDetail> {
  const index = findIndexOrThrow(familyAccessId);
  const existing = familyMembers[index];
  if (!existing) throw new Error(`Family access grant ${familyAccessId} not found`);
  if (!isFamilyAccessCancellable(existing.status)) {
    throw new Error(`Grant ${familyAccessId} cannot be resent from status ${existing.status}`);
  }

  const now = new Date();
  const invitationExpiresAt = new Date(now.getTime() + INVITATION_EXPIRY_DAYS * 86_400_000);
  const updated: FamilyMemberDetail = {
    ...existing,
    invitation_expires_at: invitationExpiresAt.toISOString(),
    history: [
      ...existing.history,
      { status: "pending", changed_at: now.toISOString(), note: "Invitation resent." },
    ],
  };

  familyMembers = [...familyMembers.slice(0, index), updated, ...familyMembers.slice(index + 1)];
  return mockFetch(updated, 500);
}
