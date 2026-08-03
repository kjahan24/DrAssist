// Temporary frontend mock repository for the current user's own
// Organization profile (`/dashboard/organization`, `/edit`). No backend
// API is consumed anywhere in this module — reads and writes an
// in-memory singleton record, standing in for the real backend
// Organization module (`app.modules.organization.domain.entities
// .Organization`) until its REST endpoints are wired up here.
//
// Like `lib/mock/profile.ts`, there is no list/params here — an
// organization overview page always shows exactly one record: the
// signed-in user's own. Seeded as `org-riverside-clinic`, the same
// organization id already used as `ORG_ID` throughout every other mock
// repository in this app.
//
// Field names are grounded in the real entity verbatim:
// `organization_code`, `name`, `legal_name`, `type` (`OrganizationType`:
// clinic/hospital/diagnostic/telemedicine), `email`, `phone`, `website`,
// `logo_url`, `registration_number`, `address`, `city`, `state`,
// `country`, `postal_code`, `timezone`, `currency`, `language`,
// `is_active`. One rename: this task's own "License Number" field maps
// to the real `registration_number` (a facility's registration/license
// number with health authorities) — the closer-sounding `tax_number`
// field also exists on the real entity but isn't modeled here since
// nothing in this task's own field list calls for a distinct tax-ID
// display.
//
// `tax_number` itself is deliberately not modeled — nothing in this
// module's UI surfaces it, the same "don't model fields nothing reads"
// discipline every other mock repository in this app already applies.

const MIN_LATENCY_MS = 350;

function mockFetch<T>(value: T, latencyMs: number = MIN_LATENCY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), latencyMs));
}

// --- Enums (verbatim from `app.modules.organization.domain.enums`) ----

export type OrganizationType = "clinic" | "hospital" | "diagnostic" | "telemedicine";

export const ORGANIZATION_TYPE_OPTIONS: { label: string; value: OrganizationType }[] = [
  { label: "Clinic", value: "clinic" },
  { label: "Hospital", value: "hospital" },
  { label: "Diagnostic Center", value: "diagnostic" },
  { label: "Telemedicine", value: "telemedicine" },
];

export function getOrganizationTypeLabel(type: OrganizationType): string {
  return ORGANIZATION_TYPE_OPTIONS.find((option) => option.value === type)?.label ?? type;
}

// --- Core shape -----------------------------------------------------

export interface Organization {
  organization_id: string;
  organization_code: string;
  name: string;
  legal_name: string | null;
  type: OrganizationType;
  logo_url: string | null;
  registration_number: string | null;
  email: string | null;
  phone: string | null;
  website: string | null;
  address: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  postal_code: string | null;
  timezone: string;
  is_active: boolean;
  created_at: string; // ISO 8601
}

let organization: Organization = {
  organization_id: "org-riverside-clinic",
  organization_code: "RIVERSIDE-01",
  name: "Riverside Clinic",
  legal_name: "Riverside Clinic Medical Group, LLC",
  type: "clinic",
  logo_url: null,
  registration_number: "TX-HC-2011-08834",
  email: "info@riversideclinic.example",
  phone: "+1 (555) 010-1000",
  website: "https://riversideclinic.example",
  address: "500 Riverside Parkway",
  city: "Austin",
  state: "TX",
  country: "United States",
  postal_code: "78701",
  timezone: "America/Chicago",
  is_active: true,
  created_at: "2011-03-15T00:00:00.000Z",
};

export function getOrganization(): Promise<Organization> {
  return mockFetch(organization, 300);
}

// `organization_code`/`is_active`/`created_at` are deliberately absent
// from this input shape — server-controlled on the real
// `PUT /organizations/{id}` endpoint, same reasoning every other
// module's own `*FormInput` type already applies. `logo_url` is written
// independently via `updateLogo()`, matching how `updateAvatar()` is
// kept separate from `updateProfile()` in `lib/mock/profile.ts`.
export interface OrganizationFormInput {
  name: string;
  legal_name: string;
  type: OrganizationType;
  registration_number: string;
  email: string;
  phone: string;
  website: string;
  address: string;
  city: string;
  state: string;
  country: string;
  postal_code: string;
  timezone: string;
}

export function organizationToFormInput(source: Organization): OrganizationFormInput {
  return {
    name: source.name,
    legal_name: source.legal_name ?? "",
    type: source.type,
    registration_number: source.registration_number ?? "",
    email: source.email ?? "",
    phone: source.phone ?? "",
    website: source.website ?? "",
    address: source.address ?? "",
    city: source.city ?? "",
    state: source.state ?? "",
    country: source.country ?? "",
    postal_code: source.postal_code ?? "",
    timezone: source.timezone,
  };
}

export function updateOrganization(input: OrganizationFormInput): Promise<Organization> {
  organization = { ...organization, ...input };
  return mockFetch(organization, 500);
}

// No real file storage exists in this mock (same "(UI)" reasoning as
// `updateAvatar()` in `lib/mock/profile.ts`) — `logoUrl` is expected to
// already be a local, browser-generated preview URL.
export function updateLogo(logoUrl: string | null): Promise<Organization> {
  organization = { ...organization, logo_url: logoUrl };
  return mockFetch(organization, 400);
}
