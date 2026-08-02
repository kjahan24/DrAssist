// Temporary frontend mock repository for Patient Management
// (`app/(dashboard)/dashboard/patients/*`). No backend API is consumed
// anywhere in this module — every function below reads from and writes
// to an in-memory array, standing in for the already-completed backend
// Patient module until its REST endpoints are wired up.
//
// Field names and the create/edit form's scope are grounded in the real
// backend contract where it's known: `Patient` stores `first_name`/
// `last_name` separately (`full_name` is derived, never stored — the
// same pattern `AuthenticatedPrincipal` already documents for `User`),
// and the real `RegisterPatient` use case only accepts core identity +
// contact fields — allergies, medications, and conditions each have
// their own dedicated backend use cases
// (`RecordPatientAllergy`/`AddPatientMedication`/
// `AddPatientMedicalCondition`), not the registration form. This mock
// repository mirrors that split deliberately: `createPatient`/
// `updatePatient` only ever touch the same fields the real registration
// endpoint will, and allergies/medications/conditions are read-only
// summaries here, matching what will eventually be true of the real API
// too (their own "add" flows are out of scope for this module).
//
// `listPatients` returns the exact `PaginatedResponse<T>` shape
// (`types/index.ts`) a real `GET /api/v1/patients` call already returns
// for every other module — swapping the mock for the real endpoint later
// changes only `features/patients/hooks/use-patients.ts`'s `queryFn`
// lines, nothing in any component.

import type { PaginatedResponse } from "@/types";

const MIN_LATENCY_MS = 350;

function mockFetch<T>(value: T, latencyMs: number = MIN_LATENCY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), latencyMs));
}

function generateId(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

// --- Shared enums -----------------------------------------------------

export type Gender = "male" | "female" | "other";
export type PatientStatus = "active" | "inactive";
export type BloodGroup = "A+" | "A-" | "B+" | "B-" | "AB+" | "AB-" | "O+" | "O-" | "unknown";

export const GENDER_OPTIONS: { label: string; value: Gender }[] = [
  { label: "Male", value: "male" },
  { label: "Female", value: "female" },
  { label: "Other", value: "other" },
];

export const BLOOD_GROUP_OPTIONS: { label: string; value: BloodGroup }[] = [
  { label: "A+", value: "A+" },
  { label: "A-", value: "A-" },
  { label: "B+", value: "B+" },
  { label: "B-", value: "B-" },
  { label: "AB+", value: "AB+" },
  { label: "AB-", value: "AB-" },
  { label: "O+", value: "O+" },
  { label: "O-", value: "O-" },
  { label: "Unknown", value: "unknown" },
];

// --- Core patient (list row) shape -------------------------------------

export interface Patient {
  patient_id: string;
  organization_id: string;
  patient_number: string;
  first_name: string;
  last_name: string;
  gender: Gender;
  date_of_birth: string; // ISO 8601 date
  blood_group: BloodGroup;
  status: PatientStatus;
  phone: string;
  email: string | null;
  last_visit_date: string | null; // ISO 8601 date
  created_at: string; // ISO 8601
}

export function getFullName(patient: Pick<Patient, "first_name" | "last_name">): string {
  return `${patient.first_name} ${patient.last_name}`;
}

export function getAge(dateOfBirth: string): number {
  const dob = new Date(dateOfBirth);
  const today = new Date();
  let age = today.getFullYear() - dob.getFullYear();
  const hasHadBirthdayThisYear =
    today.getMonth() > dob.getMonth() ||
    (today.getMonth() === dob.getMonth() && today.getDate() >= dob.getDate());
  if (!hasHadBirthdayThisYear) age -= 1;
  return age;
}

export function getInitials(patient: Pick<Patient, "first_name" | "last_name">): string {
  return `${patient.first_name[0] ?? ""}${patient.last_name[0] ?? ""}`.toUpperCase();
}

// --- Detail sub-sections -------------------------------------------------

export interface PatientContact {
  contact_id: string;
  phone: string;
  email: string | null;
  address_line1: string;
  address_line2: string | null;
  city: string;
  state: string;
  postal_code: string;
  country: string;
}

export interface EmergencyContact {
  name: string;
  relationship: string;
  phone: string;
  email: string | null;
}

export interface Insurance {
  insurance_id: string;
  provider_name: string;
  policy_number: string;
  group_number: string | null;
  coverage_type: string;
  effective_date: string;
  expiration_date: string | null;
  is_primary: boolean;
}

export type AllergyType = "food" | "medication" | "environmental" | "other";
export type AllergySeverity = "mild" | "moderate" | "severe";

export interface Allergy {
  allergy_id: string;
  allergen_name: string;
  allergy_type: AllergyType;
  severity: AllergySeverity;
  reaction: string;
  onset_date: string | null;
  status: "active" | "resolved" | "inactive";
}

export interface Medication {
  medication_id: string;
  medication_name: string;
  generic_name: string | null;
  dosage: string;
  dosage_unit: string;
  route: string;
  frequency: string;
  start_date: string;
  end_date: string | null;
  is_current: boolean;
  instructions: string | null;
}

export interface MedicalCondition {
  condition_id: string;
  condition_name: string;
  category: string | null;
  severity: "mild" | "moderate" | "severe" | null;
  diagnosis_date: string;
  icd10_code: string | null;
  status: "active" | "resolved" | "chronic";
  is_chronic: boolean;
}

export interface VitalSignsSummary {
  recorded_at: string;
  temperature_c: number;
  pulse_bpm: number;
  respiratory_rate: number;
  systolic_bp: number;
  diastolic_bp: number;
  spo2: number;
  height_cm: number;
  weight_kg: number;
  bmi: number;
}

export interface RecentVisit {
  visit_id: string;
  visit_number: string;
  visit_date: string;
  visit_type: string;
  status: string;
  doctor_name: string;
  reason_for_visit: string;
}

export interface DocumentSummary {
  document_id: string;
  file_name: string;
  category: string;
  uploaded_at: string;
}

export interface TimelineEvent {
  event_id: string;
  event_type: string;
  description: string;
  occurred_at: string;
}

export interface PatientDetail extends Patient {
  contact: PatientContact;
  emergency_contact: EmergencyContact | null;
  insurance: Insurance[];
  allergies: Allergy[];
  medications: Medication[];
  medical_conditions: MedicalCondition[];
  vital_signs: VitalSignsSummary | null;
  recent_visits: RecentVisit[];
  documents: DocumentSummary[];
  timeline_events: TimelineEvent[];
}

// --- In-memory seed data ---------------------------------------------

const ORG_ID = "org-riverside-clinic";

function daysAgo(days: number): string {
  return new Date(Date.now() - days * 86_400_000).toISOString();
}

function isoDate(year: number, month: number, day: number): string {
  return new Date(Date.UTC(year, month - 1, day)).toISOString();
}

let patients: PatientDetail[] = [
  {
    patient_id: "pat-0001",
    organization_id: ORG_ID,
    patient_number: "PAT-100001",
    first_name: "Michael",
    last_name: "Chen",
    gender: "male",
    date_of_birth: isoDate(1977, 3, 12),
    blood_group: "O+",
    status: "active",
    phone: "+1 (555) 010-1001",
    email: "michael.chen@example.com",
    last_visit_date: daysAgo(0),
    created_at: daysAgo(400),
    contact: {
      contact_id: "cont-0001",
      phone: "+1 (555) 010-1001",
      email: "michael.chen@example.com",
      address_line1: "482 Maple Street",
      address_line2: null,
      city: "Riverside",
      state: "CA",
      postal_code: "92501",
      country: "United States",
    },
    emergency_contact: {
      name: "Linda Chen",
      relationship: "Spouse",
      phone: "+1 (555) 010-1002",
      email: null,
    },
    insurance: [
      {
        insurance_id: "ins-0001",
        provider_name: "Pacific Health Partners",
        policy_number: "PHP-88213",
        group_number: "GRP-2201",
        coverage_type: "PPO",
        effective_date: isoDate(2023, 1, 1),
        expiration_date: null,
        is_primary: true,
      },
    ],
    allergies: [
      {
        allergy_id: "alg-0001",
        allergen_name: "Penicillin",
        allergy_type: "medication",
        severity: "severe",
        reaction: "Hives and difficulty breathing",
        onset_date: isoDate(2015, 6, 1),
        status: "active",
      },
    ],
    medications: [
      {
        medication_id: "med-0001",
        medication_name: "Lisinopril",
        generic_name: "Lisinopril",
        dosage: "10",
        dosage_unit: "mg",
        route: "Oral",
        frequency: "Once daily",
        start_date: isoDate(2022, 4, 10),
        end_date: null,
        is_current: true,
        instructions: "Take in the morning with water.",
      },
    ],
    medical_conditions: [
      {
        condition_id: "cond-0001",
        condition_name: "Hypertension",
        category: "Cardiovascular",
        severity: "moderate",
        diagnosis_date: isoDate(2022, 4, 10),
        icd10_code: "I10",
        status: "chronic",
        is_chronic: true,
      },
    ],
    vital_signs: {
      recorded_at: daysAgo(0),
      temperature_c: 36.8,
      pulse_bpm: 74,
      respiratory_rate: 16,
      systolic_bp: 128,
      diastolic_bp: 82,
      spo2: 98,
      height_cm: 178,
      weight_kg: 84,
      bmi: 26.5,
    },
    recent_visits: [
      {
        visit_id: "vis-0001",
        visit_number: "VIS-90001",
        visit_date: daysAgo(0),
        visit_type: "Annual Physical",
        status: "Completed",
        doctor_name: "Dr. Amara Okafor",
        reason_for_visit: "Routine annual checkup",
      },
      {
        visit_id: "vis-0002",
        visit_number: "VIS-88213",
        visit_date: daysAgo(180),
        visit_type: "Follow-up",
        status: "Completed",
        doctor_name: "Dr. Amara Okafor",
        reason_for_visit: "Blood pressure follow-up",
      },
    ],
    documents: [
      {
        document_id: "doc-0001",
        file_name: "Lab_Results_2026-01.pdf",
        category: "Lab Report",
        uploaded_at: daysAgo(2),
      },
    ],
    timeline_events: [
      {
        event_id: "evt-0001",
        event_type: "appointment_completed",
        description: "Annual physical completed",
        occurred_at: daysAgo(0),
      },
      {
        event_id: "evt-0002",
        event_type: "vital_signs_recorded",
        description: "Vital signs recorded",
        occurred_at: daysAgo(0),
      },
    ],
  },
  {
    patient_id: "pat-0002",
    organization_id: ORG_ID,
    patient_number: "PAT-100002",
    first_name: "Sarah",
    last_name: "Johnson",
    gender: "female",
    date_of_birth: isoDate(1991, 8, 22),
    blood_group: "A+",
    status: "active",
    phone: "+1 (555) 010-1003",
    email: "sarah.johnson@example.com",
    last_visit_date: daysAgo(0),
    created_at: daysAgo(250),
    contact: {
      contact_id: "cont-0002",
      phone: "+1 (555) 010-1003",
      email: "sarah.johnson@example.com",
      address_line1: "119 Oak Avenue",
      address_line2: "Apt 4B",
      city: "Riverside",
      state: "CA",
      postal_code: "92503",
      country: "United States",
    },
    emergency_contact: {
      name: "Tom Johnson",
      relationship: "Spouse",
      phone: "+1 (555) 010-1004",
      email: null,
    },
    insurance: [],
    allergies: [],
    medications: [],
    medical_conditions: [],
    vital_signs: {
      recorded_at: daysAgo(0),
      temperature_c: 36.6,
      pulse_bpm: 68,
      respiratory_rate: 14,
      systolic_bp: 112,
      diastolic_bp: 74,
      spo2: 99,
      height_cm: 165,
      weight_kg: 60,
      bmi: 22.0,
    },
    recent_visits: [
      {
        visit_id: "vis-0003",
        visit_number: "VIS-90002",
        visit_date: daysAgo(0),
        visit_type: "Follow-up",
        status: "Completed",
        doctor_name: "Dr. Amara Okafor",
        reason_for_visit: "Post-treatment follow-up",
      },
    ],
    documents: [],
    timeline_events: [
      {
        event_id: "evt-0003",
        event_type: "appointment_completed",
        description: "Follow-up visit completed",
        occurred_at: daysAgo(0),
      },
    ],
  },
  {
    patient_id: "pat-0003",
    organization_id: ORG_ID,
    patient_number: "PAT-100003",
    first_name: "Amara",
    last_name: "Nwosu",
    gender: "female",
    date_of_birth: isoDate(1964, 11, 3),
    blood_group: "B+",
    status: "active",
    phone: "+1 (555) 010-1005",
    email: "amara.nwosu@example.com",
    last_visit_date: daysAgo(2),
    created_at: daysAgo(600),
    contact: {
      contact_id: "cont-0003",
      phone: "+1 (555) 010-1005",
      email: "amara.nwosu@example.com",
      address_line1: "77 Birchwood Lane",
      address_line2: null,
      city: "Riverside",
      state: "CA",
      postal_code: "92506",
      country: "United States",
    },
    emergency_contact: {
      name: "Chidi Nwosu",
      relationship: "Son",
      phone: "+1 (555) 010-1006",
      email: "chidi.nwosu@example.com",
    },
    insurance: [
      {
        insurance_id: "ins-0002",
        provider_name: "Golden State Health",
        policy_number: "GSH-44120",
        group_number: null,
        coverage_type: "Medicare Advantage",
        effective_date: isoDate(2020, 1, 1),
        expiration_date: null,
        is_primary: true,
      },
    ],
    allergies: [
      {
        allergy_id: "alg-0002",
        allergen_name: "Shellfish",
        allergy_type: "food",
        severity: "moderate",
        reaction: "Swelling and rash",
        onset_date: null,
        status: "active",
      },
      {
        allergy_id: "alg-0003",
        allergen_name: "Latex",
        allergy_type: "environmental",
        severity: "mild",
        reaction: "Skin irritation",
        onset_date: null,
        status: "active",
      },
    ],
    medications: [
      {
        medication_id: "med-0002",
        medication_name: "Metformin",
        generic_name: "Metformin HCl",
        dosage: "500",
        dosage_unit: "mg",
        route: "Oral",
        frequency: "Twice daily",
        start_date: isoDate(2019, 9, 15),
        end_date: null,
        is_current: true,
        instructions: "Take with meals.",
      },
      {
        medication_id: "med-0003",
        medication_name: "Atorvastatin",
        generic_name: "Atorvastatin calcium",
        dosage: "20",
        dosage_unit: "mg",
        route: "Oral",
        frequency: "Once daily",
        start_date: isoDate(2021, 2, 1),
        end_date: null,
        is_current: true,
        instructions: "Take at bedtime.",
      },
    ],
    medical_conditions: [
      {
        condition_id: "cond-0002",
        condition_name: "Type 2 Diabetes Mellitus",
        category: "Endocrine",
        severity: "moderate",
        diagnosis_date: isoDate(2019, 9, 15),
        icd10_code: "E11.9",
        status: "chronic",
        is_chronic: true,
      },
      {
        condition_id: "cond-0003",
        condition_name: "Hyperlipidemia",
        category: "Cardiovascular",
        severity: "mild",
        diagnosis_date: isoDate(2021, 2, 1),
        icd10_code: "E78.5",
        status: "chronic",
        is_chronic: true,
      },
    ],
    vital_signs: {
      recorded_at: daysAgo(2),
      temperature_c: 37.0,
      pulse_bpm: 80,
      respiratory_rate: 18,
      systolic_bp: 134,
      diastolic_bp: 86,
      spo2: 97,
      height_cm: 160,
      weight_kg: 72,
      bmi: 28.1,
    },
    recent_visits: [
      {
        visit_id: "vis-0004",
        visit_number: "VIS-89765",
        visit_date: daysAgo(2),
        visit_type: "Follow-up",
        status: "Completed",
        doctor_name: "Dr. Amara Okafor",
        reason_for_visit: "Diabetes management review",
      },
    ],
    documents: [
      {
        document_id: "doc-0002",
        file_name: "Insurance_Card.pdf",
        category: "Insurance",
        uploaded_at: daysAgo(3),
      },
      {
        document_id: "doc-0003",
        file_name: "A1C_Panel_2026-01.pdf",
        category: "Lab Report",
        uploaded_at: daysAgo(2),
      },
    ],
    timeline_events: [
      {
        event_id: "evt-0004",
        event_type: "document_uploaded",
        description: "Patient uploaded a document",
        occurred_at: daysAgo(3),
      },
      {
        event_id: "evt-0005",
        event_type: "appointment_completed",
        description: "Diabetes management review completed",
        occurred_at: daysAgo(2),
      },
    ],
  },
];

// Remaining seed patients are lighter (list-only depth) to keep this file
// a reasonable size — every one still has the full `PatientDetail` shape,
// just with simpler/empty sub-sections, which is itself a realistic mix
// (most patients don't have allergies, active medications, etc.).
const LIGHT_SEED: Array<{
  first_name: string;
  last_name: string;
  gender: Gender;
  dob: string;
  blood_group: BloodGroup;
  status: PatientStatus;
  lastVisitDaysAgo: number | null;
}> = [
  {
    first_name: "David",
    last_name: "Kim",
    gender: "male",
    dob: isoDate(1985, 5, 30),
    blood_group: "AB+",
    status: "active",
    lastVisitDaysAgo: 1,
  },
  {
    first_name: "Priya",
    last_name: "Patel",
    gender: "female",
    dob: isoDate(1996, 2, 14),
    blood_group: "O-",
    status: "active",
    lastVisitDaysAgo: 1,
  },
  {
    first_name: "James",
    last_name: "Williams",
    gender: "male",
    dob: isoDate(1958, 9, 9),
    blood_group: "A-",
    status: "active",
    lastVisitDaysAgo: 1,
  },
  {
    first_name: "Olivia",
    last_name: "Martinez",
    gender: "female",
    dob: isoDate(2001, 12, 1),
    blood_group: "B-",
    status: "active",
    lastVisitDaysAgo: 5,
  },
  {
    first_name: "Ethan",
    last_name: "Brown",
    gender: "male",
    dob: isoDate(1972, 7, 19),
    blood_group: "O+",
    status: "active",
    lastVisitDaysAgo: 8,
  },
  {
    first_name: "Grace",
    last_name: "Nguyen",
    gender: "female",
    dob: isoDate(1988, 4, 25),
    blood_group: "AB-",
    status: "inactive",
    lastVisitDaysAgo: 220,
  },
  {
    first_name: "Lucas",
    last_name: "Anderson",
    gender: "male",
    dob: isoDate(1994, 10, 5),
    blood_group: "A+",
    status: "active",
    lastVisitDaysAgo: 14,
  },
  {
    first_name: "Robert",
    last_name: "Lee",
    gender: "male",
    dob: isoDate(1969, 1, 17),
    blood_group: "B+",
    status: "active",
    lastVisitDaysAgo: 4,
  },
  {
    first_name: "Emma",
    last_name: "Garcia",
    gender: "female",
    dob: isoDate(1999, 6, 8),
    blood_group: "O+",
    status: "active",
    lastVisitDaysAgo: 30,
  },
  {
    first_name: "Noah",
    last_name: "Thompson",
    gender: "male",
    dob: isoDate(1980, 3, 3),
    blood_group: "unknown",
    status: "inactive",
    lastVisitDaysAgo: 400,
  },
  {
    first_name: "Ava",
    last_name: "Rodriguez",
    gender: "female",
    dob: isoDate(2010, 8, 12),
    blood_group: "A+",
    status: "active",
    lastVisitDaysAgo: 45,
  },
  {
    first_name: "William",
    last_name: "Davis",
    gender: "male",
    dob: isoDate(1950, 11, 28),
    blood_group: "O-",
    status: "active",
    lastVisitDaysAgo: 6,
  },
  {
    first_name: "Sofia",
    last_name: "Torres",
    gender: "female",
    dob: isoDate(1993, 5, 16),
    blood_group: "B-",
    status: "active",
    lastVisitDaysAgo: null,
  },
  {
    first_name: "Benjamin",
    last_name: "White",
    gender: "male",
    dob: isoDate(1976, 2, 2),
    blood_group: "AB+",
    status: "active",
    lastVisitDaysAgo: 60,
  },
  {
    first_name: "Isabella",
    last_name: "Clark",
    gender: "female",
    dob: isoDate(2015, 9, 21),
    blood_group: "A-",
    status: "active",
    lastVisitDaysAgo: 90,
  },
];

LIGHT_SEED.forEach((seed, index) => {
  const num = index + 4;
  const id = `pat-${String(num).padStart(4, "0")}`;
  patients.push({
    patient_id: id,
    organization_id: ORG_ID,
    patient_number: `PAT-${100000 + num}`,
    first_name: seed.first_name,
    last_name: seed.last_name,
    gender: seed.gender,
    date_of_birth: seed.dob,
    blood_group: seed.blood_group,
    status: seed.status,
    phone: `+1 (555) 010-${1000 + num * 3}`,
    email: `${seed.first_name.toLowerCase()}.${seed.last_name.toLowerCase()}@example.com`,
    last_visit_date: seed.lastVisitDaysAgo === null ? null : daysAgo(seed.lastVisitDaysAgo),
    created_at: daysAgo(200 + num * 10),
    contact: {
      contact_id: `cont-${id}`,
      phone: `+1 (555) 010-${1000 + num * 3}`,
      email: `${seed.first_name.toLowerCase()}.${seed.last_name.toLowerCase()}@example.com`,
      address_line1: `${100 + num} Willow Court`,
      address_line2: null,
      city: "Riverside",
      state: "CA",
      postal_code: "92500",
      country: "United States",
    },
    emergency_contact: null,
    insurance: [],
    allergies: [],
    medications: [],
    medical_conditions: [],
    vital_signs: null,
    recent_visits:
      seed.lastVisitDaysAgo === null
        ? []
        : [
            {
              visit_id: `vis-${id}`,
              visit_number: `VIS-${89000 + num}`,
              visit_date: daysAgo(seed.lastVisitDaysAgo),
              visit_type: "Follow-up",
              status: "Completed",
              doctor_name: "Dr. Amara Okafor",
              reason_for_visit: "Routine visit",
            },
          ],
    documents: [],
    timeline_events: [],
  });
});

// --- Repository: reads -----------------------------------------------

export interface PatientListParams {
  search?: string;
  status?: PatientStatus | "all";
  gender?: Gender | "all";
  sortBy?: keyof Patient;
  sortDirection?: "asc" | "desc";
  page?: number;
  pageSize?: number;
}

function matchesSearch(patient: Patient, search: string): boolean {
  const needle = search.trim().toLowerCase();
  if (!needle) return true;
  return (
    getFullName(patient).toLowerCase().includes(needle) ||
    patient.patient_number.toLowerCase().includes(needle) ||
    patient.phone.toLowerCase().includes(needle) ||
    (patient.email ?? "").toLowerCase().includes(needle)
  );
}

export function listPatients(params: PatientListParams = {}): Promise<PaginatedResponse<Patient>> {
  const {
    search = "",
    status = "all",
    gender = "all",
    sortBy = "last_name",
    sortDirection = "asc",
    page = 1,
    pageSize = 10,
  } = params;

  let filtered = patients.filter((patient) => matchesSearch(patient, search));
  if (status !== "all") {
    filtered = filtered.filter((patient) => patient.status === status);
  }
  if (gender !== "all") {
    filtered = filtered.filter((patient) => patient.gender === gender);
  }

  const sorted = [...filtered].sort((a, b) => {
    const left = a[sortBy];
    const right = b[sortBy];
    const comparison = String(left ?? "").localeCompare(String(right ?? ""));
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

function stripDetail(patient: PatientDetail): Patient {
  return {
    patient_id: patient.patient_id,
    organization_id: patient.organization_id,
    patient_number: patient.patient_number,
    first_name: patient.first_name,
    last_name: patient.last_name,
    gender: patient.gender,
    date_of_birth: patient.date_of_birth,
    blood_group: patient.blood_group,
    status: patient.status,
    phone: patient.phone,
    email: patient.email,
    last_visit_date: patient.last_visit_date,
    created_at: patient.created_at,
  };
}

export function getPatient(patientId: string): Promise<PatientDetail | null> {
  const found = patients.find((patient) => patient.patient_id === patientId) ?? null;
  return mockFetch(found, 300);
}

// --- Repository: writes -------------------------------------------------
// Deliberately the same field set the real `RegisterPatient`/future
// `UpdatePatient` backend use cases accept — see this file's own
// docstring.

export interface PatientFormInput {
  first_name: string;
  last_name: string;
  gender: Gender;
  date_of_birth: string;
  blood_group: BloodGroup;
  status: PatientStatus;
  phone: string;
  email: string;
  address_line1: string;
  address_line2: string;
  city: string;
  state: string;
  postal_code: string;
  emergency_contact_name: string;
  emergency_contact_relationship: string;
  emergency_contact_phone: string;
  insurance_provider: string;
  insurance_policy_number: string;
}

export async function createPatient(input: PatientFormInput): Promise<PatientDetail> {
  const id = generateId("pat");
  const nextNumber = 100000 + patients.length + 1;

  const created: PatientDetail = {
    patient_id: id,
    organization_id: ORG_ID,
    patient_number: `PAT-${nextNumber}`,
    first_name: input.first_name,
    last_name: input.last_name,
    gender: input.gender,
    date_of_birth: input.date_of_birth,
    blood_group: input.blood_group,
    status: input.status,
    phone: input.phone,
    email: input.email || null,
    last_visit_date: null,
    created_at: new Date().toISOString(),
    contact: {
      contact_id: generateId("cont"),
      phone: input.phone,
      email: input.email || null,
      address_line1: input.address_line1,
      address_line2: input.address_line2 || null,
      city: input.city,
      state: input.state,
      postal_code: input.postal_code,
      country: "United States",
    },
    emergency_contact: input.emergency_contact_name
      ? {
          name: input.emergency_contact_name,
          relationship: input.emergency_contact_relationship,
          phone: input.emergency_contact_phone,
          email: null,
        }
      : null,
    insurance: input.insurance_provider
      ? [
          {
            insurance_id: generateId("ins"),
            provider_name: input.insurance_provider,
            policy_number: input.insurance_policy_number,
            group_number: null,
            coverage_type: "PPO",
            effective_date: new Date().toISOString(),
            expiration_date: null,
            is_primary: true,
          },
        ]
      : [],
    allergies: [],
    medications: [],
    medical_conditions: [],
    vital_signs: null,
    recent_visits: [],
    documents: [],
    timeline_events: [],
  };

  patients = [created, ...patients];
  return mockFetch(created, 500);
}

export async function updatePatient(
  patientId: string,
  input: PatientFormInput,
): Promise<PatientDetail> {
  const index = patients.findIndex((patient) => patient.patient_id === patientId);
  if (index === -1) {
    throw new Error(`Patient ${patientId} not found`);
  }

  const existing = patients[index];
  if (!existing) {
    throw new Error(`Patient ${patientId} not found`);
  }

  const updated: PatientDetail = {
    ...existing,
    first_name: input.first_name,
    last_name: input.last_name,
    gender: input.gender,
    date_of_birth: input.date_of_birth,
    blood_group: input.blood_group,
    status: input.status,
    phone: input.phone,
    email: input.email || null,
    contact: {
      ...existing.contact,
      phone: input.phone,
      email: input.email || null,
      address_line1: input.address_line1,
      address_line2: input.address_line2 || null,
      city: input.city,
      state: input.state,
      postal_code: input.postal_code,
    },
    emergency_contact: input.emergency_contact_name
      ? {
          name: input.emergency_contact_name,
          relationship: input.emergency_contact_relationship,
          phone: input.emergency_contact_phone,
          email: existing.emergency_contact?.email ?? null,
        }
      : existing.emergency_contact,
  };

  patients = [...patients.slice(0, index), updated, ...patients.slice(index + 1)];
  return mockFetch(updated, 500);
}

export function patientToFormInput(patient: PatientDetail): PatientFormInput {
  return {
    first_name: patient.first_name,
    last_name: patient.last_name,
    gender: patient.gender,
    date_of_birth: patient.date_of_birth.slice(0, 10),
    blood_group: patient.blood_group,
    status: patient.status,
    phone: patient.phone,
    email: patient.email ?? "",
    address_line1: patient.contact.address_line1,
    address_line2: patient.contact.address_line2 ?? "",
    city: patient.contact.city,
    state: patient.contact.state,
    postal_code: patient.contact.postal_code,
    emergency_contact_name: patient.emergency_contact?.name ?? "",
    emergency_contact_relationship: patient.emergency_contact?.relationship ?? "",
    emergency_contact_phone: patient.emergency_contact?.phone ?? "",
    insurance_provider: patient.insurance[0]?.provider_name ?? "",
    insurance_policy_number: patient.insurance[0]?.policy_number ?? "",
  };
}
