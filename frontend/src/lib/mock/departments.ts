// Temporary frontend mock repository for Department management
// (`/dashboard/organization/departments`). No backend API is consumed
// anywhere in this module — every function below reads from an
// in-memory array, standing in for the real backend Organization
// module's `Department` aggregate
// (`app.modules.organization.domain.entities.Department`) until its REST
// endpoints are wired up here.
//
// `name`, `description`, `status` (`DepartmentStatus`: active/inactive)
// are grounded verbatim in the real entity. Two fields have no backend
// basis at all, called out explicitly:
//   - `head_of_department_name` — the real `Department` entity has no
//     "head" field or relationship of any kind.
//   - `member_count` — the real entity has no member roster of its own
//     either (staff-to-department assignment isn't modeled as a
//     `Department` field, it lives on the assigning side). Computed here
//     by keeping this file's seed counts in sync with
//     `lib/mock/members.ts`'s own seed data by hand (both are new mock
//     files introduced together in this module) rather than via a
//     cross-file lookup, the same "small, hand-verified seed
//     consistency" approach used wherever two sibling mock files
//     describe the same small dataset from two angles.
//
// Department names match `lib/mock/doctors.ts`'s existing
// `department` field values exactly (General Medicine, Cardiology,
// Pediatrics, Orthopedics, Dermatology, Obstetrics & Gynecology,
// Neurology, Behavioral Health) for consistency across the app, even
// though that file's own docstring notes `department` isn't a modeled
// relationship on the real `Doctor` entity either — this module is what
// finally gives departments their own real (if still frontend-mocked)
// identity.

const MIN_LATENCY_MS = 300;

function mockFetch<T>(value: T, latencyMs: number = MIN_LATENCY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), latencyMs));
}

export type DepartmentStatus = "active" | "inactive";

export const DEPARTMENT_STATUS_OPTIONS: { label: string; value: DepartmentStatus }[] = [
  { label: "Active", value: "active" },
  { label: "Inactive", value: "inactive" },
];

export function getDepartmentStatusLabel(status: DepartmentStatus): string {
  return DEPARTMENT_STATUS_OPTIONS.find((option) => option.value === status)?.label ?? status;
}

export interface Department {
  department_id: string;
  organization_id: string;
  name: string;
  description: string | null;
  head_of_department_name: string | null;
  member_count: number;
  status: DepartmentStatus;
  created_at: string; // ISO 8601
}

const ORG_ID = "org-riverside-clinic";

interface DepartmentSeed {
  name: string;
  description: string;
  head_of_department_name: string;
  member_count: number;
  status: DepartmentStatus;
}

// `member_count` here matches how many seeded `lib/mock/members.ts`
// rows carry this exact department name — see this file's own docstring.
const SEED: DepartmentSeed[] = [
  {
    name: "General Medicine",
    description: "Primary and preventive care for adult patients.",
    head_of_department_name: "Dr. Amara Okafor",
    member_count: 2,
    status: "active",
  },
  {
    name: "Cardiology",
    description: "Diagnosis and treatment of heart and vascular conditions.",
    head_of_department_name: "Dr. Daniel Reyes",
    member_count: 2,
    status: "active",
  },
  {
    name: "Pediatrics",
    description: "Medical care for infants, children, and adolescents.",
    head_of_department_name: "Dr. Priya Sharma",
    member_count: 2,
    status: "active",
  },
  {
    name: "Orthopedics",
    description: "Treatment of musculoskeletal conditions and injuries.",
    head_of_department_name: "Dr. Marcus Webb",
    member_count: 1,
    status: "active",
  },
  {
    name: "Dermatology",
    description: "Diagnosis and treatment of skin, hair, and nail conditions.",
    head_of_department_name: "Dr. Hannah Kim",
    member_count: 2,
    status: "active",
  },
  {
    name: "Obstetrics & Gynecology",
    description: "Women's reproductive health and maternity care.",
    head_of_department_name: "Dr. Elena Petrova",
    member_count: 1,
    status: "active",
  },
  {
    name: "Neurology",
    description: "Diagnosis and treatment of nervous system disorders.",
    head_of_department_name: "Dr. Samuel Osei",
    member_count: 1,
    status: "inactive",
  },
  {
    name: "Behavioral Health",
    description: "Mental health assessment, therapy, and psychiatric care.",
    head_of_department_name: "Dr. Grace Liu",
    member_count: 1,
    status: "active",
  },
];

const departments: Department[] = SEED.map((seed, index) => ({
  department_id: `dept-${String(index + 1).padStart(4, "0")}`,
  organization_id: ORG_ID,
  name: seed.name,
  description: seed.description,
  head_of_department_name: seed.head_of_department_name,
  member_count: seed.member_count,
  status: seed.status,
  created_at: "2015-01-01T00:00:00.000Z",
}));

export interface DepartmentListParams {
  search?: string;
  status?: DepartmentStatus | "all";
  sortBy?: "name" | "member_count" | "status";
  sortDirection?: "asc" | "desc";
}

function matchesSearch(department: Department, search: string): boolean {
  const needle = search.trim().toLowerCase();
  if (!needle) return true;
  return (
    department.name.toLowerCase().includes(needle) ||
    (department.head_of_department_name?.toLowerCase().includes(needle) ?? false)
  );
}

// Returns a plain array, not `PaginatedResponse<T>` — a real
// organization has a small, bounded number of departments, the same
// "small reference dataset" reasoning `lib/mock/doctors.ts` already
// applies to its own `listDoctors()`.
export function listDepartments(params: DepartmentListParams = {}): Promise<Department[]> {
  const { search = "", status = "all", sortBy = "name", sortDirection = "asc" } = params;

  let filtered = departments.filter((department) => matchesSearch(department, search));
  if (status !== "all") filtered = filtered.filter((department) => department.status === status);

  const sorted = [...filtered].sort((a, b) => {
    const comparison =
      sortBy === "member_count"
        ? a.member_count - b.member_count
        : String(a[sortBy]).localeCompare(String(b[sortBy]));
    return sortDirection === "asc" ? comparison : -comparison;
  });

  return mockFetch(sorted);
}

export function getDepartment(departmentId: string): Promise<Department | null> {
  const found = departments.find((department) => department.department_id === departmentId) ?? null;
  return mockFetch(found, 200);
}
