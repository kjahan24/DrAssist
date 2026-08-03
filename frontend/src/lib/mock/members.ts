// Temporary frontend mock repository for Organization Members
// (`/dashboard/organization/members`). No backend API is consumed
// anywhere in this module — every function below reads from an
// in-memory array, standing in for a real backend endpoint that would
// join the Authentication module's `User`/`Role` aggregates
// (`app.modules.authentication.domain.entities`) scoped to one
// organization.
//
// `first_name`/`last_name`/`email`/`phone`/`status` are grounded
// verbatim in the real `User` entity; `status` (`MemberStatus`) matches
// `UserStatus` exactly (invited/active/suspended/deactivated).
// `last_active_at` maps to the real `User.last_login_at`.
//
// Two fields are denormalized rather than modeled as real FKs, called
// out explicitly:
//   - `role_name` — the real `User` entity has no direct role field;
//     role assignment is a separate relationship the Authentication
//     module's `Role` aggregate participates in, not shown here as a
//     live join. Seeded with real `Role.name`-shaped values (e.g.
//     "Doctor", "Front Desk Coordinator") rather than a `role_id`, the
//     same denormalized-display-field convention every mock repository
//     in this app already uses for cross-module names.
//   - `department_id`/`department_name` — the real `User` entity has no
//     department field either; department membership isn't modeled on
//     either side in the real backend yet. Values here are kept in sync
//     by hand with `lib/mock/departments.ts`'s own `member_count`
//     fields — see that file's own docstring.

const MIN_LATENCY_MS = 350;

function mockFetch<T>(value: T, latencyMs: number = MIN_LATENCY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), latencyMs));
}

// --- Status (verbatim from `app.modules.authentication.domain.enums.UserStatus`) --

export type MemberStatus = "invited" | "active" | "suspended" | "deactivated";

export const MEMBER_STATUS_OPTIONS: { label: string; value: MemberStatus }[] = [
  { label: "Invited", value: "invited" },
  { label: "Active", value: "active" },
  { label: "Suspended", value: "suspended" },
  { label: "Deactivated", value: "deactivated" },
];

export function getMemberStatusLabel(status: MemberStatus): string {
  return MEMBER_STATUS_OPTIONS.find((option) => option.value === status)?.label ?? status;
}

// --- Core shape -----------------------------------------------------

export interface Member {
  member_id: string;
  organization_id: string;
  full_name: string;
  email: string;
  phone: string | null;
  role_name: string;
  department_id: string | null;
  department_name: string | null;
  status: MemberStatus;
  last_active_at: string | null; // ISO 8601
  invited_at: string; // ISO 8601
}

const ORG_ID = "org-riverside-clinic";

function daysAgo(days: number): string {
  return new Date(Date.now() - days * 86_400_000).toISOString();
}

interface MemberSeed {
  full_name: string;
  email: string;
  phone: string;
  role_name: string;
  department_id: string | null;
  department_name: string | null;
  status: MemberStatus;
  invitedDaysAgo: number;
  lastActiveHoursAgo: number | null;
}

// `department_id` values match `dept-0001`..`dept-0008`, the exact ids
// `lib/mock/departments.ts` generates for its own 8 seeded rows in
// declaration order (General Medicine, Cardiology, Pediatrics,
// Orthopedics, Dermatology, Obstetrics & Gynecology, Neurology,
// Behavioral Health).
const SEED: MemberSeed[] = [
  {
    full_name: "Dr. Amara Okafor",
    email: "amara.okafor@riversideclinic.example",
    phone: "+1 (555) 010-2244",
    role_name: "Doctor",
    department_id: "dept-0001",
    department_name: "General Medicine",
    status: "active",
    invitedDaysAgo: 4000,
    lastActiveHoursAgo: 0.2,
  },
  {
    full_name: "Dr. Daniel Reyes",
    email: "daniel.reyes@riversideclinic.example",
    phone: "+1 (555) 010-2245",
    role_name: "Doctor",
    department_id: "dept-0002",
    department_name: "Cardiology",
    status: "active",
    invitedDaysAgo: 3200,
    lastActiveHoursAgo: 3,
  },
  {
    full_name: "Dr. Priya Sharma",
    email: "priya.sharma@riversideclinic.example",
    phone: "+1 (555) 010-2246",
    role_name: "Doctor",
    department_id: "dept-0003",
    department_name: "Pediatrics",
    status: "active",
    invitedDaysAgo: 2600,
    lastActiveHoursAgo: 20,
  },
  {
    full_name: "Dr. Marcus Webb",
    email: "marcus.webb@riversideclinic.example",
    phone: "+1 (555) 010-2247",
    role_name: "Doctor",
    department_id: "dept-0004",
    department_name: "Orthopedics",
    status: "active",
    invitedDaysAgo: 1900,
    lastActiveHoursAgo: 30,
  },
  {
    full_name: "Dr. Hannah Kim",
    email: "hannah.kim@riversideclinic.example",
    phone: "+1 (555) 010-2248",
    role_name: "Doctor",
    department_id: "dept-0005",
    department_name: "Dermatology",
    status: "active",
    invitedDaysAgo: 1500,
    lastActiveHoursAgo: 6,
  },
  {
    full_name: "Dr. Elena Petrova",
    email: "elena.petrova@riversideclinic.example",
    phone: "+1 (555) 010-2249",
    role_name: "Doctor",
    department_id: "dept-0006",
    department_name: "Obstetrics & Gynecology",
    status: "active",
    invitedDaysAgo: 1200,
    lastActiveHoursAgo: 48,
  },
  {
    full_name: "Dr. Samuel Osei",
    email: "samuel.osei@riversideclinic.example",
    phone: "+1 (555) 010-2250",
    role_name: "Doctor",
    department_id: "dept-0007",
    department_name: "Neurology",
    status: "suspended",
    invitedDaysAgo: 900,
    lastActiveHoursAgo: 2400,
  },
  {
    full_name: "Dr. Grace Liu",
    email: "grace.liu@riversideclinic.example",
    phone: "+1 (555) 010-2251",
    role_name: "Doctor",
    department_id: "dept-0008",
    department_name: "Behavioral Health",
    status: "active",
    invitedDaysAgo: 700,
    lastActiveHoursAgo: 12,
  },
  {
    full_name: "Jordan Lee",
    email: "jordan.lee@riversideclinic.example",
    phone: "+1 (555) 010-3301",
    role_name: "Front Desk Coordinator",
    department_id: "dept-0001",
    department_name: "General Medicine",
    status: "active",
    invitedDaysAgo: 600,
    lastActiveHoursAgo: 1,
  },
  {
    full_name: "Maria Gonzalez",
    email: "maria.gonzalez@riversideclinic.example",
    phone: "+1 (555) 010-3302",
    role_name: "Registered Nurse",
    department_id: "dept-0002",
    department_name: "Cardiology",
    status: "active",
    invitedDaysAgo: 500,
    lastActiveHoursAgo: 5,
  },
  {
    full_name: "Thomas Baker",
    email: "thomas.baker@riversideclinic.example",
    phone: "+1 (555) 010-3303",
    role_name: "Administrator",
    department_id: null,
    department_name: null,
    status: "active",
    invitedDaysAgo: 4000,
    lastActiveHoursAgo: 0.5,
  },
  {
    full_name: "Susan Patel",
    email: "susan.patel@riversideclinic.example",
    phone: "+1 (555) 010-3304",
    role_name: "Billing Specialist",
    department_id: null,
    department_name: null,
    status: "active",
    invitedDaysAgo: 450,
    lastActiveHoursAgo: 26,
  },
  {
    full_name: "Kevin Chen",
    email: "kevin.chen.staff@riversideclinic.example",
    phone: "+1 (555) 010-3305",
    role_name: "Nurse",
    department_id: "dept-0003",
    department_name: "Pediatrics",
    status: "invited",
    invitedDaysAgo: 2,
    lastActiveHoursAgo: null,
  },
  {
    full_name: "Olivia Turner",
    email: "olivia.turner@riversideclinic.example",
    phone: "+1 (555) 010-3306",
    role_name: "Medical Assistant",
    department_id: "dept-0005",
    department_name: "Dermatology",
    status: "deactivated",
    invitedDaysAgo: 1100,
    lastActiveHoursAgo: 2200,
  },
];

const members: Member[] = SEED.map((seed, index) => ({
  member_id: `mem-${String(index + 1).padStart(4, "0")}`,
  organization_id: ORG_ID,
  full_name: seed.full_name,
  email: seed.email,
  phone: seed.phone,
  role_name: seed.role_name,
  department_id: seed.department_id,
  department_name: seed.department_name,
  status: seed.status,
  last_active_at:
    seed.lastActiveHoursAgo === null
      ? null
      : new Date(Date.now() - seed.lastActiveHoursAgo * 3_600_000).toISOString(),
  invited_at: daysAgo(seed.invitedDaysAgo),
}));

export interface MemberListParams {
  search?: string;
  status?: MemberStatus | "all";
  departmentId?: string | "all";
  sortBy?: "full_name" | "role_name" | "department_name" | "status" | "last_active_at";
  sortDirection?: "asc" | "desc";
  page?: number;
  pageSize?: number;
}

function matchesSearch(member: Member, search: string): boolean {
  const needle = search.trim().toLowerCase();
  if (!needle) return true;
  return (
    member.full_name.toLowerCase().includes(needle) ||
    member.email.toLowerCase().includes(needle) ||
    member.role_name.toLowerCase().includes(needle)
  );
}

function sortValue(member: Member, sortBy: NonNullable<MemberListParams["sortBy"]>): string {
  return member[sortBy] ?? "";
}

export interface MemberPage {
  items: Member[];
  total: number;
  page: number;
  page_size: number;
}

export function listMembers(params: MemberListParams = {}): Promise<MemberPage> {
  const {
    search = "",
    status = "all",
    departmentId = "all",
    sortBy = "full_name",
    sortDirection = "asc",
    page = 1,
    pageSize = 10,
  } = params;

  let filtered = members.filter((member) => matchesSearch(member, search));
  if (status !== "all") filtered = filtered.filter((member) => member.status === status);
  if (departmentId !== "all")
    filtered = filtered.filter((member) => member.department_id === departmentId);

  const sorted = [...filtered].sort((a, b) => {
    const comparison = sortValue(a, sortBy).localeCompare(sortValue(b, sortBy));
    return sortDirection === "asc" ? comparison : -comparison;
  });

  const offset = (page - 1) * pageSize;
  return mockFetch({
    items: sorted.slice(offset, offset + pageSize),
    total: sorted.length,
    page,
    page_size: pageSize,
  });
}

export function getMember(memberId: string): Promise<Member | null> {
  const found = members.find((member) => member.member_id === memberId) ?? null;
  return mockFetch(found, 200);
}
