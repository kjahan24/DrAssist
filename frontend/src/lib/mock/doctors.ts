// Temporary frontend mock repository for doctor reference data, used by
// the Appointment Management module's doctor selector
// (`features/appointments/components/doctor-combobox.tsx`).
//
// The real backend has no single flattened "doctor with name and
// specialty" read model — `DoctorSummaryDTO` (doctor_id, user_id,
// employee_id, status), `DoctorProfileSummaryDTO` (full_name, gender,
// phone, email, qualification, ...), and `DoctorSpecializationSummaryDTO`
// (specialization_name, is_primary) are three separate DTOs
// (`app.modules.doctor.application.dto`). `Doctor` below is the frontend's
// own flattened combination of those three, grounded field-for-field in
// their real names (`doctor_id`, `full_name`, `specialization_name`,
// `status`) — a real API would either return a pre-joined summary shape
// like this one or require three calls per doctor, so this is the
// reasonable shape to build against.
//
// `department` is explicitly NOT part of any real backend Doctor entity —
// the backend's `Department` entity (`app.modules.organization`) has no
// linkage to `Doctor` at all yet. It's included here purely as a mock
// display/filter convenience for the Appointment list's "Department"
// column; swapping this repository for a real API later means either
// dropping that column or deriving it once the backend adds the
// relationship.

const MIN_LATENCY_MS = 250;

function mockFetch<T>(value: T, latencyMs: number = MIN_LATENCY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), latencyMs));
}

export type DoctorStatus = "active" | "inactive" | "suspended";

export interface Doctor {
  doctor_id: string;
  full_name: string;
  specialization_name: string;
  department: string;
  status: DoctorStatus;
}

export function getDoctorInitials(doctor: Pick<Doctor, "full_name">): string {
  return doctor.full_name
    .split(" ")
    .map((part) => part[0] ?? "")
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

const doctors: Doctor[] = [
  {
    doctor_id: "doc-0001",
    full_name: "Dr. Amara Okafor",
    specialization_name: "Internal Medicine",
    department: "General Medicine",
    status: "active",
  },
  {
    doctor_id: "doc-0002",
    full_name: "Dr. Daniel Reyes",
    specialization_name: "Cardiology",
    department: "Cardiology",
    status: "active",
  },
  {
    doctor_id: "doc-0003",
    full_name: "Dr. Priya Sharma",
    specialization_name: "Pediatrics",
    department: "Pediatrics",
    status: "active",
  },
  {
    doctor_id: "doc-0004",
    full_name: "Dr. Marcus Webb",
    specialization_name: "Orthopedic Surgery",
    department: "Orthopedics",
    status: "active",
  },
  {
    doctor_id: "doc-0005",
    full_name: "Dr. Hannah Kim",
    specialization_name: "Dermatology",
    department: "Dermatology",
    status: "active",
  },
  {
    doctor_id: "doc-0006",
    full_name: "Dr. Elena Petrova",
    specialization_name: "Obstetrics & Gynecology",
    department: "Obstetrics & Gynecology",
    status: "active",
  },
  {
    doctor_id: "doc-0007",
    full_name: "Dr. Samuel Osei",
    specialization_name: "Neurology",
    department: "Neurology",
    status: "inactive",
  },
  {
    doctor_id: "doc-0008",
    full_name: "Dr. Grace Liu",
    specialization_name: "Psychiatry",
    department: "Behavioral Health",
    status: "active",
  },
];

export interface DoctorListParams {
  search?: string;
}

// Returns a plain array, not `PaginatedResponse<T>` — this backs a
// typeahead selector over a small reference dataset, not a paged list
// page, and a real API for this would most likely be a dedicated
// lightweight lookup endpoint rather than the paginated `/doctors` list.
export function listDoctors(params: DoctorListParams = {}): Promise<Doctor[]> {
  const needle = (params.search ?? "").trim().toLowerCase();
  const active = doctors.filter((doctor) => doctor.status === "active");
  const filtered = needle
    ? active.filter(
        (doctor) =>
          doctor.full_name.toLowerCase().includes(needle) ||
          doctor.specialization_name.toLowerCase().includes(needle) ||
          doctor.department.toLowerCase().includes(needle),
      )
    : active;
  return mockFetch(filtered);
}

export function getDoctor(doctorId: string): Promise<Doctor | null> {
  const found = doctors.find((doctor) => doctor.doctor_id === doctorId) ?? null;
  return mockFetch(found);
}
