// Temporary frontend mock repository for Visit Management
// (`app/(dashboard)/dashboard/visits/*`). No backend API is consumed
// anywhere in this module — every function below reads from and writes
// to an in-memory array, standing in for the backend Visit module
// (`app.modules.visit`) until its REST endpoints grow beyond their
// current scope (today: `POST /visits`, `GET /visits/{id}`,
// `GET /visits`, `GET /visits/patient/{id}` — no update/status-change
// endpoints exist yet, so this mock's `updateVisit` has no real
// counterpart to match against; it's shaped defensively, matching the
// same field set `createVisit` accepts).
//
// Field names are grounded in the real domain entity
// (`app.modules.visit.domain.entities.PatientVisit`): `patient_id,
// doctor_id, visit_number, visit_type, visit_date, appointment_id,
// visit_status, check_in_time, consultation_start_time,
// consultation_end_time, chief_complaint_summary, notes`.
// `VisitType`/`VisitStatus` match `domain/enums.py` verbatim.
//
// The backend's Visit module is deliberately a thin foundation — SOAP
// notes, diagnoses, prescriptions, vital signs, and attachments are each
// their own sibling module anchored on `visit_id`
// (`app.modules.soap_notes`, `.diagnosis`, `.prescriptions`,
// `.vital_signs`, `.attachments`), not nested inside Visit itself. This
// mock mirrors that split: `SOAPNote`, `VisitDiagnosis`,
// `VisitPrescription`/`PrescriptionItem`, `VisitVitalSigns`, and
// `VisitDocument` are each grounded field-for-field in their real
// sibling entities, just attached here as sub-arrays on `VisitDetail`
// for convenience, since this mock has no reason to run five separate
// repositories.
//
// Two simplifications, called out because they don't map to anything
// real:
//   - `timeline_events` — like Appointment's `status_history`, the real
//     backend only fires one domain event per transition
//     (`PatientVisitCheckedIn`, `PatientVisitConsultationStarted`, ...),
//     no queryable log. Generated deterministically from each seeded
//     visit's final status.
//   - `patient_name`/`patient_number`/`doctor_name`/`department` are
//     denormalized display fields, same reasoning as
//     `lib/mock/appointments.ts`'s identical fields.
// `SOAPNote.vital_sign_summary` (a free-text field on the real entity)
// and `PatientVisit.check_out_time`/`room_number`/`follow_up_*` are
// deliberately not modeled — nothing in this module's UI surfaces them,
// and modeling fields no component reads would just be dead weight.

import type { PaginatedResponse } from "@/types";

const MIN_LATENCY_MS = 350;

function mockFetch<T>(value: T, latencyMs: number = MIN_LATENCY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), latencyMs));
}

function generateId(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

// --- Enums (verbatim from `app.modules.visit.domain.enums`) -----------

export type VisitType =
  | "consultation"
  | "follow_up"
  | "emergency"
  | "telemedicine"
  | "procedure"
  | "lab_review"
  | "vaccination"
  | "home_visit";

export type VisitStatus =
  "scheduled" | "checked_in" | "in_progress" | "completed" | "cancelled" | "no_show";

export const VISIT_TYPE_OPTIONS: { label: string; value: VisitType }[] = [
  { label: "Consultation", value: "consultation" },
  { label: "Follow-up", value: "follow_up" },
  { label: "Emergency", value: "emergency" },
  { label: "Telemedicine", value: "telemedicine" },
  { label: "Procedure", value: "procedure" },
  { label: "Lab Review", value: "lab_review" },
  { label: "Vaccination", value: "vaccination" },
  { label: "Home Visit", value: "home_visit" },
];

export const VISIT_STATUS_OPTIONS: { label: string; value: VisitStatus }[] = [
  { label: "Scheduled", value: "scheduled" },
  { label: "Checked In", value: "checked_in" },
  { label: "In Progress", value: "in_progress" },
  { label: "Completed", value: "completed" },
  { label: "Cancelled", value: "cancelled" },
  { label: "No Show", value: "no_show" },
];

export function getVisitTypeLabel(type: VisitType): string {
  return VISIT_TYPE_OPTIONS.find((option) => option.value === type)?.label ?? type;
}

export function getVisitStatusLabel(status: VisitStatus): string {
  return VISIT_STATUS_OPTIONS.find((option) => option.value === status)?.label ?? status;
}

// --- Sub-resource shapes (each grounded in its own sibling module) ------

export interface VisitVitalSigns {
  recorded_at: string;
  temperature_c: number;
  pulse_bpm: number;
  respiratory_rate: number;
  systolic_bp: number;
  diastolic_bp: number;
  spo2: number;
  height_cm: number | null;
  weight_kg: number | null;
  bmi: number | null;
  blood_glucose: number | null;
  pain_score: number | null;
}

export interface SOAPNote {
  chief_complaint: string | null;
  history_of_present_illness: string | null;
  review_of_systems: string | null;
  physical_examination: string | null;
  assessment: string | null;
  plan: string | null;
}

export type DiagnosisType = "primary" | "secondary" | "differential";
export type DiagnosisStatus = "provisional" | "confirmed" | "ruled_out";

export interface VisitDiagnosis {
  diagnosis_id: string;
  sequence_number: number;
  diagnosis_name: string;
  diagnosis_type: DiagnosisType;
  icd10_code: string | null;
  diagnosis_status: DiagnosisStatus;
  diagnosed_at: string;
  clinical_notes: string | null;
}

export type PrescriptionStatus = "draft" | "final";
export type AdministrationRoute =
  | "oral"
  | "iv"
  | "im"
  | "sc"
  | "topical"
  | "inhalation"
  | "ophthalmic"
  | "otic"
  | "nasal"
  | "rectal"
  | "vaginal"
  | "other";

export interface PrescriptionItem {
  item_id: string;
  medication_name: string;
  generic_name: string | null;
  strength: string;
  dosage: string;
  dosage_unit: string;
  route: AdministrationRoute;
  frequency: string;
  duration: string;
  duration_unit: string;
  quantity: string;
  instructions: string | null;
}

export interface VisitPrescription {
  prescription_id: string;
  prescription_number: string;
  prescription_date: string;
  status: PrescriptionStatus;
  notes: string | null;
  items: PrescriptionItem[];
}

export type AttachmentType = "image" | "pdf" | "document" | "audio" | "video" | "other";

export interface VisitDocument {
  document_id: string;
  file_name: string;
  attachment_type: AttachmentType;
  mime_type: string;
  file_size_bytes: number;
  uploaded_at: string;
  description: string | null;
}

export interface VisitTimelineEvent {
  event_id: string;
  description: string;
  occurred_at: string;
}

// --- Core shapes ---------------------------------------------------------

export interface Visit {
  visit_id: string;
  organization_id: string;
  visit_number: string;
  patient_id: string;
  patient_name: string;
  patient_number: string;
  doctor_id: string;
  doctor_name: string;
  department: string;
  appointment_id: string | null;
  visit_date: string; // ISO 8601 date ("YYYY-MM-DD")
  visit_type: VisitType;
  visit_status: VisitStatus;
  chief_complaint_summary: string | null;
  created_at: string; // ISO 8601
}

export interface VisitDetail extends Visit {
  notes: string | null;
  check_in_time: string | null;
  consultation_start_time: string | null;
  consultation_end_time: string | null;
  vital_signs: VisitVitalSigns | null;
  soap_note: SOAPNote | null;
  diagnoses: VisitDiagnosis[];
  prescription: VisitPrescription | null;
  documents: VisitDocument[];
  timeline_events: VisitTimelineEvent[];
}

export function getPatientInitials(visit: Pick<Visit, "patient_name">): string {
  return visit.patient_name
    .split(" ")
    .map((part) => part[0] ?? "")
    .join("")
    .slice(0, 2)
    .toUpperCase();
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

function buildVisitProgress(
  status: VisitStatus,
  createdAt: Date,
  checkInAt: Date,
  consultStartAt: Date,
  consultEndAt: Date,
): {
  timeline_events: VisitTimelineEvent[];
  check_in_time: string | null;
  consultation_start_time: string | null;
  consultation_end_time: string | null;
} {
  const events: VisitTimelineEvent[] = [
    {
      event_id: generateId("evt"),
      description: "Visit scheduled",
      occurred_at: createdAt.toISOString(),
    },
  ];

  if (status === "cancelled") {
    events.push({
      event_id: generateId("evt"),
      description: "Visit cancelled",
      occurred_at: new Date(createdAt.getTime() + 2 * 60 * 60_000).toISOString(),
    });
    return {
      timeline_events: events,
      check_in_time: null,
      consultation_start_time: null,
      consultation_end_time: null,
    };
  }

  if (status === "no_show") {
    events.push({
      event_id: generateId("evt"),
      description: "Patient marked as no-show",
      occurred_at: new Date(checkInAt.getTime() + 15 * 60_000).toISOString(),
    });
    return {
      timeline_events: events,
      check_in_time: null,
      consultation_start_time: null,
      consultation_end_time: null,
    };
  }

  if (status === "scheduled") {
    return {
      timeline_events: events,
      check_in_time: null,
      consultation_start_time: null,
      consultation_end_time: null,
    };
  }

  events.push({
    event_id: generateId("evt"),
    description: "Patient checked in",
    occurred_at: checkInAt.toISOString(),
  });
  if (status === "checked_in") {
    return {
      timeline_events: events,
      check_in_time: checkInAt.toISOString(),
      consultation_start_time: null,
      consultation_end_time: null,
    };
  }

  events.push({
    event_id: generateId("evt"),
    description: "Consultation started",
    occurred_at: consultStartAt.toISOString(),
  });
  if (status === "in_progress") {
    return {
      timeline_events: events,
      check_in_time: checkInAt.toISOString(),
      consultation_start_time: consultStartAt.toISOString(),
      consultation_end_time: null,
    };
  }

  events.push({
    event_id: generateId("evt"),
    description: "Consultation completed",
    occurred_at: consultEndAt.toISOString(),
  });
  return {
    timeline_events: events,
    check_in_time: checkInAt.toISOString(),
    consultation_start_time: consultStartAt.toISOString(),
    consultation_end_time: consultEndAt.toISOString(),
  };
}

interface VisitSeed {
  patient_id: string;
  patient_name: string;
  patient_number: string;
  doctor_id: string;
  doctor_name: string;
  department: string;
  appointment_id: string | null;
  dayOffset: number;
  nominalTime: string;
  visit_type: VisitType;
  status: VisitStatus;
  chief_complaint_summary: string;
  rich?: boolean;
}

const SEED: VisitSeed[] = [
  {
    patient_id: "pat-0001",
    patient_name: "Michael Chen",
    patient_number: "PAT-100001",
    doctor_id: "doc-0001",
    doctor_name: "Dr. Amara Okafor",
    department: "General Medicine",
    appointment_id: "apt-0001",
    dayOffset: 0,
    nominalTime: "09:00",
    visit_type: "consultation",
    status: "completed",
    chief_complaint_summary: "Annual checkup, no acute complaints",
    rich: true,
  },
  {
    patient_id: "pat-0002",
    patient_name: "Sarah Johnson",
    patient_number: "PAT-100002",
    doctor_id: "doc-0001",
    doctor_name: "Dr. Amara Okafor",
    department: "General Medicine",
    appointment_id: "apt-0002",
    dayOffset: 0,
    nominalTime: "09:30",
    visit_type: "follow_up",
    status: "completed",
    chief_complaint_summary: "Follow-up post-treatment, feeling better",
    rich: true,
  },
  {
    patient_id: "pat-0004",
    patient_name: "David Kim",
    patient_number: "PAT-100004",
    doctor_id: "doc-0002",
    doctor_name: "Dr. Daniel Reyes",
    department: "Cardiology",
    appointment_id: "apt-0004",
    dayOffset: -1,
    nominalTime: "10:00",
    visit_type: "consultation",
    status: "completed",
    chief_complaint_summary: "Chest pain, EKG performed",
    rich: true,
  },
  {
    patient_id: "pat-0003",
    patient_name: "Amara Nwosu",
    patient_number: "PAT-100003",
    doctor_id: "doc-0001",
    doctor_name: "Dr. Amara Okafor",
    department: "General Medicine",
    appointment_id: "apt-0003",
    dayOffset: -2,
    nominalTime: "14:00",
    visit_type: "follow_up",
    status: "completed",
    chief_complaint_summary: "Diabetes review, blood sugar stable",
  },
  {
    patient_id: "pat-0006",
    patient_name: "James Williams",
    patient_number: "PAT-100006",
    doctor_id: "doc-0004",
    doctor_name: "Dr. Marcus Webb",
    department: "Orthopedics",
    appointment_id: "apt-0006",
    dayOffset: -3,
    nominalTime: "13:00",
    visit_type: "procedure",
    status: "completed",
    chief_complaint_summary: "Knee injection administered",
  },
  {
    patient_id: "pat-0011",
    patient_name: "Robert Lee",
    patient_number: "PAT-100011",
    doctor_id: "doc-0004",
    doctor_name: "Dr. Marcus Webb",
    department: "Orthopedics",
    appointment_id: null,
    dayOffset: -1,
    nominalTime: "15:00",
    visit_type: "follow_up",
    status: "completed",
    chief_complaint_summary: "Post-surgical wound check",
  },
  {
    patient_id: "pat-0013",
    patient_name: "Noah Thompson",
    patient_number: "PAT-100013",
    doctor_id: "doc-0001",
    doctor_name: "Dr. Amara Okafor",
    department: "General Medicine",
    appointment_id: null,
    dayOffset: -4,
    nominalTime: "11:00",
    visit_type: "consultation",
    status: "completed",
    chief_complaint_summary: "Medication review",
  },
  {
    patient_id: "pat-0016",
    patient_name: "Sofia Torres",
    patient_number: "PAT-100016",
    doctor_id: "doc-0005",
    doctor_name: "Dr. Hannah Kim",
    department: "Dermatology",
    appointment_id: null,
    dayOffset: -6,
    nominalTime: "13:30",
    visit_type: "consultation",
    status: "completed",
    chief_complaint_summary: "Mole biopsy sent to lab",
  },
  {
    patient_id: "pat-0014",
    patient_name: "Ava Rodriguez",
    patient_number: "PAT-100014",
    doctor_id: "doc-0003",
    doctor_name: "Dr. Priya Sharma",
    department: "Pediatrics",
    appointment_id: null,
    dayOffset: -10,
    nominalTime: "09:00",
    visit_type: "vaccination",
    status: "completed",
    chief_complaint_summary: "Annual flu vaccination",
  },
  {
    patient_id: "pat-0008",
    patient_name: "Ethan Brown",
    patient_number: "PAT-100008",
    doctor_id: "doc-0001",
    doctor_name: "Dr. Amara Okafor",
    department: "General Medicine",
    appointment_id: "apt-0008",
    dayOffset: 0,
    nominalTime: "10:30",
    visit_type: "consultation",
    status: "in_progress",
    chief_complaint_summary: "Hypertension medication follow-up",
  },
  {
    patient_id: "pat-0009",
    patient_name: "Grace Nguyen",
    patient_number: "PAT-100009",
    doctor_id: "doc-0006",
    doctor_name: "Dr. Elena Petrova",
    department: "Obstetrics & Gynecology",
    appointment_id: "apt-0009",
    dayOffset: 0,
    nominalTime: "11:00",
    visit_type: "consultation",
    status: "checked_in",
    chief_complaint_summary: "Prenatal checkup",
  },
  {
    patient_id: "pat-0005",
    patient_name: "Priya Patel",
    patient_number: "PAT-100005",
    doctor_id: "doc-0003",
    doctor_name: "Dr. Priya Sharma",
    department: "Pediatrics",
    appointment_id: "apt-0005",
    dayOffset: -1,
    nominalTime: "11:00",
    visit_type: "consultation",
    status: "no_show",
    chief_complaint_summary: "Well-child visit",
  },
  {
    patient_id: "pat-0007",
    patient_name: "Olivia Martinez",
    patient_number: "PAT-100007",
    doctor_id: "doc-0005",
    doctor_name: "Dr. Hannah Kim",
    department: "Dermatology",
    appointment_id: "apt-0007",
    dayOffset: -5,
    nominalTime: "15:00",
    visit_type: "consultation",
    status: "cancelled",
    chief_complaint_summary: "Skin rash evaluation",
  },
  {
    patient_id: "pat-0010",
    patient_name: "Lucas Anderson",
    patient_number: "PAT-100010",
    doctor_id: "doc-0002",
    doctor_name: "Dr. Daniel Reyes",
    department: "Cardiology",
    appointment_id: "apt-0010",
    dayOffset: 1,
    nominalTime: "09:00",
    visit_type: "consultation",
    status: "scheduled",
    chief_complaint_summary: "Cardiac follow-up",
  },
  {
    patient_id: "pat-0012",
    patient_name: "Emma Garcia",
    patient_number: "PAT-100012",
    doctor_id: "doc-0008",
    doctor_name: "Dr. Grace Liu",
    department: "Behavioral Health",
    appointment_id: "apt-0012",
    dayOffset: 2,
    nominalTime: "14:00",
    visit_type: "consultation",
    status: "scheduled",
    chief_complaint_summary: "Anxiety management session",
  },
  {
    patient_id: "pat-0017",
    patient_name: "Benjamin White",
    patient_number: "PAT-100017",
    doctor_id: "doc-0004",
    doctor_name: "Dr. Marcus Webb",
    department: "Orthopedics",
    appointment_id: "apt-0017",
    dayOffset: 5,
    nominalTime: "10:00",
    visit_type: "emergency",
    status: "scheduled",
    chief_complaint_summary: "Acute back pain evaluation",
  },
];

function buildRichSubResources(
  seed: VisitSeed,
  visitId: string,
): {
  vital_signs: VisitVitalSigns | null;
  soap_note: SOAPNote | null;
  diagnoses: VisitDiagnosis[];
  prescription: VisitPrescription | null;
  documents: VisitDocument[];
} {
  if (!seed.rich) {
    return { vital_signs: null, soap_note: null, diagnoses: [], prescription: null, documents: [] };
  }

  const recordedAt = atTime(dateOffset(seed.dayOffset), seed.nominalTime);

  return {
    vital_signs: {
      recorded_at: recordedAt.toISOString(),
      temperature_c: 36.8,
      pulse_bpm: 74,
      respiratory_rate: 16,
      systolic_bp: 126,
      diastolic_bp: 80,
      spo2: 98,
      height_cm: 175,
      weight_kg: 80,
      bmi: 26.1,
      blood_glucose: 98,
      pain_score: 1,
    },
    soap_note: {
      chief_complaint: seed.chief_complaint_summary,
      history_of_present_illness:
        "Patient reports gradual onset of symptoms over the past two weeks, no prior similar episodes.",
      review_of_systems:
        "No fever, no chest pain, no shortness of breath. Appetite and sleep normal.",
      physical_examination:
        "Alert and oriented. Heart and lung sounds normal. No acute distress observed.",
      assessment:
        "Stable, consistent with chronic condition management; no new concerns identified.",
      plan: "Continue current treatment plan, follow up in 3 months, patient education provided.",
    },
    diagnoses: [
      {
        diagnosis_id: generateId("dx"),
        sequence_number: 1,
        diagnosis_name: "Essential hypertension",
        diagnosis_type: "primary",
        icd10_code: "I10",
        diagnosis_status: "confirmed",
        diagnosed_at: recordedAt.toISOString(),
        clinical_notes: "Blood pressure well controlled on current regimen.",
      },
    ],
    prescription: {
      prescription_id: generateId("rx"),
      prescription_number: `RX-${70000 + Number(visitId.slice(-4))}`,
      prescription_date: dateOffset(seed.dayOffset),
      status: "final",
      notes: "Continue as directed, refill in 90 days.",
      items: [
        {
          item_id: generateId("rxi"),
          medication_name: "Lisinopril",
          generic_name: "Lisinopril",
          strength: "10 mg",
          dosage: "1 tablet",
          dosage_unit: "tablet",
          route: "oral",
          frequency: "Once daily",
          duration: "90",
          duration_unit: "days",
          quantity: "90",
          instructions: "Take in the morning with water.",
        },
      ],
    },
    documents: [
      {
        document_id: generateId("doc"),
        file_name: `Visit_Summary_${dateOffset(seed.dayOffset)}.pdf`,
        attachment_type: "pdf",
        mime_type: "application/pdf",
        file_size_bytes: 245_000,
        uploaded_at: recordedAt.toISOString(),
        description: "Visit summary and after-visit instructions.",
      },
    ],
  };
}

let visits: VisitDetail[] = SEED.map((seed, index) => {
  const num = index + 1;
  const visit_id = `vis8-${String(num).padStart(4, "0")}`;
  const visit_date = dateOffset(seed.dayOffset);
  const nominalStart = atTime(visit_date, seed.nominalTime);
  const createdAt = new Date(nominalStart.getTime() - (2 + (num % 4)) * 24 * 60 * 60_000);
  const checkInAt = new Date(nominalStart.getTime() - 10 * 60_000);
  const consultStartAt = nominalStart;
  const consultEndAt = new Date(nominalStart.getTime() + 25 * 60_000);

  const progress = buildVisitProgress(
    seed.status,
    createdAt,
    checkInAt,
    consultStartAt,
    consultEndAt,
  );
  const subResources = buildRichSubResources(seed, visit_id);

  return {
    visit_id,
    organization_id: ORG_ID,
    visit_number: `VIS-${80000 + num}`,
    patient_id: seed.patient_id,
    patient_name: seed.patient_name,
    patient_number: seed.patient_number,
    doctor_id: seed.doctor_id,
    doctor_name: seed.doctor_name,
    department: seed.department,
    appointment_id: seed.appointment_id,
    visit_date,
    visit_type: seed.visit_type,
    visit_status: seed.status,
    chief_complaint_summary: seed.chief_complaint_summary,
    created_at: createdAt.toISOString(),
    notes: seed.rich ? "No unusual findings during this visit." : null,
    check_in_time: progress.check_in_time,
    consultation_start_time: progress.consultation_start_time,
    consultation_end_time: progress.consultation_end_time,
    timeline_events: progress.timeline_events,
    ...subResources,
  };
});

// --- Repository: reads -----------------------------------------------

export interface VisitListParams {
  search?: string;
  status?: VisitStatus | "all";
  visitType?: VisitType | "all";
  sortBy?: "visit_date" | "patient_name" | "doctor_name" | "status";
  sortDirection?: "asc" | "desc";
  page?: number;
  pageSize?: number;
}

function matchesSearch(visit: Visit, search: string): boolean {
  const needle = search.trim().toLowerCase();
  if (!needle) return true;
  return (
    visit.visit_number.toLowerCase().includes(needle) ||
    visit.patient_name.toLowerCase().includes(needle) ||
    visit.doctor_name.toLowerCase().includes(needle) ||
    (visit.chief_complaint_summary ?? "").toLowerCase().includes(needle)
  );
}

function sortKey(visit: Visit, sortBy: NonNullable<VisitListParams["sortBy"]>): string {
  if (sortBy === "status") return visit.visit_status;
  if (sortBy === "visit_date") return visit.visit_date;
  return String(visit[sortBy]);
}

function stripDetail(visit: VisitDetail): Visit {
  return {
    visit_id: visit.visit_id,
    organization_id: visit.organization_id,
    visit_number: visit.visit_number,
    patient_id: visit.patient_id,
    patient_name: visit.patient_name,
    patient_number: visit.patient_number,
    doctor_id: visit.doctor_id,
    doctor_name: visit.doctor_name,
    department: visit.department,
    appointment_id: visit.appointment_id,
    visit_date: visit.visit_date,
    visit_type: visit.visit_type,
    visit_status: visit.visit_status,
    chief_complaint_summary: visit.chief_complaint_summary,
    created_at: visit.created_at,
  };
}

export function listVisits(params: VisitListParams = {}): Promise<PaginatedResponse<Visit>> {
  const {
    search = "",
    status = "all",
    visitType = "all",
    sortBy = "visit_date",
    sortDirection = "desc",
    page = 1,
    pageSize = 10,
  } = params;

  let filtered = visits.filter((visit) => matchesSearch(visit, search));
  if (status !== "all") {
    filtered = filtered.filter((visit) => visit.visit_status === status);
  }
  if (visitType !== "all") {
    filtered = filtered.filter((visit) => visit.visit_type === visitType);
  }

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

export function getVisit(visitId: string): Promise<VisitDetail | null> {
  const found = visits.find((visit) => visit.visit_id === visitId) ?? null;
  return mockFetch(found, 300);
}

// --- Repository: writes -------------------------------------------------
// Deliberately the same field set the real `ScheduleVisitRequest` accepts
// — see this file's own docstring. `visit_status` is never client-set,
// matching the real API (every new visit starts `scheduled`).

export interface VisitFormInput {
  patient_id: string;
  doctor_id: string;
  appointment_id: string;
  visit_date: string;
  visit_type: VisitType;
  chief_complaint_summary: string;
  notes: string;
}

function resolvePatientDisplay(patientId: string): { name: string; number: string } {
  const existing = visits.find((visit) => visit.patient_id === patientId);
  return existing
    ? { name: existing.patient_name, number: existing.patient_number }
    : { name: "Unknown Patient", number: "—" };
}

function resolveDoctorDisplay(doctorId: string): { name: string; department: string } {
  const existing = visits.find((visit) => visit.doctor_id === doctorId);
  return existing
    ? { name: existing.doctor_name, department: existing.department }
    : { name: "Unknown Doctor", department: "—" };
}

export async function createVisit(input: VisitFormInput): Promise<VisitDetail> {
  const id = generateId("vis8");
  const nextNumber = 80000 + visits.length + 1;
  const patient = resolvePatientDisplay(input.patient_id);
  const doctor = resolveDoctorDisplay(input.doctor_id);
  const now = new Date();

  const created: VisitDetail = {
    visit_id: id,
    organization_id: ORG_ID,
    visit_number: `VIS-${nextNumber}`,
    patient_id: input.patient_id,
    patient_name: patient.name,
    patient_number: patient.number,
    doctor_id: input.doctor_id,
    doctor_name: doctor.name,
    department: doctor.department,
    appointment_id: input.appointment_id || null,
    visit_date: input.visit_date,
    visit_type: input.visit_type,
    visit_status: "scheduled",
    chief_complaint_summary: input.chief_complaint_summary || null,
    created_at: now.toISOString(),
    notes: input.notes || null,
    check_in_time: null,
    consultation_start_time: null,
    consultation_end_time: null,
    vital_signs: null,
    soap_note: null,
    diagnoses: [],
    prescription: null,
    documents: [],
    timeline_events: [
      {
        event_id: generateId("evt"),
        description: "Visit scheduled",
        occurred_at: now.toISOString(),
      },
    ],
  };

  visits = [created, ...visits];
  return mockFetch(created, 500);
}

export async function updateVisit(visitId: string, input: VisitFormInput): Promise<VisitDetail> {
  const index = visits.findIndex((visit) => visit.visit_id === visitId);
  const existing = visits[index];
  if (!existing) {
    throw new Error(`Visit ${visitId} not found`);
  }

  const patient =
    input.patient_id === existing.patient_id
      ? { name: existing.patient_name, number: existing.patient_number }
      : resolvePatientDisplay(input.patient_id);
  const doctor =
    input.doctor_id === existing.doctor_id
      ? { name: existing.doctor_name, department: existing.department }
      : resolveDoctorDisplay(input.doctor_id);

  const updated: VisitDetail = {
    ...existing,
    patient_id: input.patient_id,
    patient_name: patient.name,
    patient_number: patient.number,
    doctor_id: input.doctor_id,
    doctor_name: doctor.name,
    department: doctor.department,
    appointment_id: input.appointment_id || null,
    visit_date: input.visit_date,
    visit_type: input.visit_type,
    chief_complaint_summary: input.chief_complaint_summary || null,
    notes: input.notes || null,
  };

  visits = [...visits.slice(0, index), updated, ...visits.slice(index + 1)];
  return mockFetch(updated, 500);
}

export function visitToFormInput(visit: VisitDetail): VisitFormInput {
  return {
    patient_id: visit.patient_id,
    doctor_id: visit.doctor_id,
    appointment_id: visit.appointment_id ?? "",
    visit_date: visit.visit_date,
    visit_type: visit.visit_type,
    chief_complaint_summary: visit.chief_complaint_summary ?? "",
    notes: visit.notes ?? "",
  };
}
