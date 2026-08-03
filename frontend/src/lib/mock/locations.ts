// Temporary frontend mock repository for Facility Locations
// (`/dashboard/organization/locations`). No backend API is consumed
// anywhere in this module.
//
// **This entire file has no real backend basis.** Unlike every sibling
// mock file in this module, there is no `OrganizationLocation` (or
// equivalent) entity anywhere in this codebase — the closest thing is a
// passing mention in `app.modules.organization.domain.entities`'s own
// module docstring ("the same reason `OrganizationLocation` was kept
// independent of `Organization`"), which refers to an architecture
// decision for an entity that was never actually implemented. Every
// field here is therefore a frontend invention scoped to exactly this
// task's own "Locations: Facility Name, Address, Contact, Operating
// Hours, Status" requirement, grounded only in plausible real-world
// multi-location clinic data, not any backend contract. `organization_id`
// is the one field that *would* be real once a backend entity exists,
// included now so the shape is a reasonable drop-in target later.

const MIN_LATENCY_MS = 300;

function mockFetch<T>(value: T, latencyMs: number = MIN_LATENCY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), latencyMs));
}

export type LocationStatus = "active" | "inactive" | "under_maintenance";

export const LOCATION_STATUS_OPTIONS: { label: string; value: LocationStatus }[] = [
  { label: "Active", value: "active" },
  { label: "Inactive", value: "inactive" },
  { label: "Under Maintenance", value: "under_maintenance" },
];

export function getLocationStatusLabel(status: LocationStatus): string {
  return LOCATION_STATUS_OPTIONS.find((option) => option.value === status)?.label ?? status;
}

export interface OperatingHoursEntry {
  day: "Monday" | "Tuesday" | "Wednesday" | "Thursday" | "Friday" | "Saturday" | "Sunday";
  open_time: string | null; // "HH:mm", null when closed that day
  close_time: string | null;
}

const WEEKDAYS: OperatingHoursEntry["day"][] = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

function weekdayHours(
  open: string,
  close: string,
  weekendOpen: string | null = null,
  weekendClose: string | null = null,
): OperatingHoursEntry[] {
  return WEEKDAYS.map((day) => {
    const isWeekend = day === "Saturday" || day === "Sunday";
    if (isWeekend) {
      return { day, open_time: weekendOpen, close_time: weekendClose };
    }
    return { day, open_time: open, close_time: close };
  });
}

export interface Location {
  location_id: string;
  organization_id: string;
  facility_name: string;
  address: string;
  city: string;
  state: string;
  country: string;
  postal_code: string;
  phone: string;
  email: string | null;
  operating_hours: OperatingHoursEntry[];
  status: LocationStatus;
  is_primary: boolean;
  created_at: string; // ISO 8601
}

const ORG_ID = "org-riverside-clinic";

const locations: Location[] = [
  {
    location_id: "loc-0001",
    organization_id: ORG_ID,
    facility_name: "Riverside Clinic — Main Campus",
    address: "500 Riverside Parkway",
    city: "Austin",
    state: "TX",
    country: "United States",
    postal_code: "78701",
    phone: "+1 (555) 010-1000",
    email: "mainclinic@riversideclinic.example",
    operating_hours: weekdayHours("08:00", "18:00", "09:00", "13:00"),
    status: "active",
    is_primary: true,
    created_at: "2011-03-15T00:00:00.000Z",
  },
  {
    location_id: "loc-0002",
    organization_id: ORG_ID,
    facility_name: "Riverside Clinic — North Branch",
    address: "1420 Parmer Lane",
    city: "Austin",
    state: "TX",
    country: "United States",
    postal_code: "78727",
    phone: "+1 (555) 010-2200",
    email: "northbranch@riversideclinic.example",
    operating_hours: weekdayHours("08:00", "17:00"),
    status: "active",
    is_primary: false,
    created_at: "2016-09-01T00:00:00.000Z",
  },
  {
    location_id: "loc-0003",
    organization_id: ORG_ID,
    facility_name: "Riverside Diagnostic Center",
    address: "88 Congress Avenue",
    city: "Austin",
    state: "TX",
    country: "United States",
    postal_code: "78701",
    phone: "+1 (555) 010-3300",
    email: "diagnostics@riversideclinic.example",
    operating_hours: weekdayHours("07:00", "19:00", "08:00", "14:00"),
    status: "under_maintenance",
    is_primary: false,
    created_at: "2019-05-10T00:00:00.000Z",
  },
  {
    location_id: "loc-0004",
    organization_id: ORG_ID,
    facility_name: "Riverside Telemedicine Hub",
    address: "500 Riverside Parkway, Suite 300",
    city: "Austin",
    state: "TX",
    country: "United States",
    postal_code: "78701",
    phone: "+1 (555) 010-4400",
    email: "telehealth@riversideclinic.example",
    operating_hours: weekdayHours("00:00", "23:59", "00:00", "23:59"),
    status: "active",
    is_primary: false,
    created_at: "2022-01-20T00:00:00.000Z",
  },
];

export interface LocationListParams {
  search?: string;
  status?: LocationStatus | "all";
  sortBy?: "facility_name" | "city" | "status";
  sortDirection?: "asc" | "desc";
}

function matchesSearch(location: Location, search: string): boolean {
  const needle = search.trim().toLowerCase();
  if (!needle) return true;
  return (
    location.facility_name.toLowerCase().includes(needle) ||
    location.address.toLowerCase().includes(needle) ||
    location.city.toLowerCase().includes(needle)
  );
}

// Plain array, not `PaginatedResponse<T>` — same "small reference
// dataset" reasoning as `lib/mock/departments.ts`.
export function listLocations(params: LocationListParams = {}): Promise<Location[]> {
  const { search = "", status = "all", sortBy = "facility_name", sortDirection = "asc" } = params;

  let filtered = locations.filter((location) => matchesSearch(location, search));
  if (status !== "all") filtered = filtered.filter((location) => location.status === status);

  const sorted = [...filtered].sort((a, b) => {
    const comparison = String(a[sortBy]).localeCompare(String(b[sortBy]));
    return sortDirection === "asc" ? comparison : -comparison;
  });

  return mockFetch(sorted);
}

export function getLocation(locationId: string): Promise<Location | null> {
  const found = locations.find((location) => location.location_id === locationId) ?? null;
  return mockFetch(found, 200);
}
