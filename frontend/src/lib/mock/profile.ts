// Temporary frontend mock repository for the current user's own Doctor
// Profile (`/dashboard/profile`). No backend API is consumed anywhere in
// this module — reads and writes an in-memory singleton record, standing
// in for the real backend Doctor module
// (`app.modules.doctor.application.dto.DoctorProfileSummaryDTO` /
// `DoctorSummaryDTO` / `DoctorLicenseSummaryDTO`) until its REST
// endpoints are wired up here.
//
// Unlike every other `lib/mock/*.ts` file, this one has no list/params —
// a profile page always shows exactly one record: the signed-in user's
// own. Seeded as `doc-0001` / "Dr. Amara Okafor", the same doctor
// identity already used as the implicit "current user" throughout this
// app (e.g. the Notifications recipient, the Family Access "Invited By"
// name) — see `lib/mock/doctors.ts`.
//
// Field names are grounded in the real DTOs:
//   - `full_name`, `email`, `phone`, `address`, `biography`,
//     `years_of_experience` — `DoctorProfileSummaryDTO` verbatim.
//   - `avatar_url` — `DoctorProfileSummaryDTO.profile_photo_url`, renamed
//     to match this task's own "Avatar" field naming.
//   - `professional_title` — `DoctorProfileSummaryDTO.qualification`,
//     renamed: this task asks for a "Professional Title" field
//     specifically, and a real qualification string (e.g. "MD, Board
//     Certified — Internal Medicine") reads naturally as one. There is
//     no *separate* real field for a role/seniority title distinct from
//     qualification.
//   - `specialization_name` — `AddDoctorSpecializationInput
//     .specialization_name` (the doctor's primary specialization).
//   - `license_number` — `DoctorLicenseSummaryDTO.license_number`.
//   - `employee_id`, `joining_date`, `status` — `DoctorSummaryDTO`
//     verbatim.
//
// `organization_name` is a denormalized display field, same reasoning as
// every other mock repository in this app. License Number and
// Organization are intentionally not part of `ProfileFormInput` below —
// changing either goes through the real backend's own distinct
// `AddDoctorLicense`/org-membership use cases, not a self-service
// profile edit, so `ProfileForm` renders them read-only.

const MIN_LATENCY_MS = 350;

function mockFetch<T>(value: T, latencyMs: number = MIN_LATENCY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), latencyMs));
}

export interface DoctorProfile {
  doctor_id: string;
  user_id: string;
  organization_id: string;
  organization_name: string;
  employee_id: string;
  full_name: string;
  professional_title: string;
  specialization_name: string;
  license_number: string;
  email: string;
  phone: string;
  address: string;
  biography: string;
  years_of_experience: number;
  avatar_url: string | null;
  joining_date: string; // ISO 8601 date
}

let profile: DoctorProfile = {
  doctor_id: "doc-0001",
  user_id: "user-current",
  organization_id: "org-riverside-clinic",
  organization_name: "Riverside Clinic",
  employee_id: "EMP-1001",
  full_name: "Dr. Amara Okafor",
  professional_title: "MD, Board Certified — Internal Medicine",
  specialization_name: "Internal Medicine",
  license_number: "MD-2015-04471",
  email: "amara.okafor@riversideclinic.example",
  phone: "+1 (555) 010-2244",
  address: "500 Riverside Parkway, Austin, TX 78701",
  biography:
    "Dr. Okafor has over a decade of experience in internal medicine, focusing on preventive care and chronic disease management. She earned her MD from the University of Texas and completed her residency at Riverside Clinic, where she now leads the General Medicine department.",
  years_of_experience: 11,
  avatar_url: null,
  joining_date: "2015-06-01",
};

export function getProfile(): Promise<DoctorProfile> {
  return mockFetch(profile, 300);
}

// `avatar_url` is intentionally omitted here — `AvatarUploader` writes
// it directly via `updateAvatar()` below, independent of the rest of the
// form, matching how a real avatar-upload endpoint would be a separate
// multipart request from a JSON profile-fields update.
export interface ProfileFormInput {
  full_name: string;
  professional_title: string;
  specialization_name: string;
  email: string;
  phone: string;
  address: string;
  biography: string;
}

export function profileToFormInput(source: DoctorProfile): ProfileFormInput {
  return {
    full_name: source.full_name,
    professional_title: source.professional_title,
    specialization_name: source.specialization_name,
    email: source.email,
    phone: source.phone,
    address: source.address,
    biography: source.biography,
  };
}

export function updateProfile(input: ProfileFormInput): Promise<DoctorProfile> {
  profile = { ...profile, ...input };
  return mockFetch(profile, 500);
}

// No real file storage exists in this mock (same "(UI)" reasoning as
// every other upload surface in this app) — `avatarUrl` is expected to
// already be a local, browser-generated preview URL (`URL.createObjectURL`)
// from `AvatarUploader`, not an uploaded file.
export function updateAvatar(avatarUrl: string | null): Promise<DoctorProfile> {
  profile = { ...profile, avatar_url: avatarUrl };
  return mockFetch(profile, 400);
}
