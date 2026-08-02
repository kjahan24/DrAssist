// Temporary frontend mock repository for Clinical Notes Management
// (`app/(dashboard)/dashboard/clinical-notes/*`). No backend API is
// consumed anywhere in this module — every function below reads from and
// writes to an in-memory array, standing in for the backend Clinical
// Notes module (`app.modules.clinical_notes`) until its REST endpoints
// grow beyond their current scope (today: `POST /`, `GET /{id}`,
// `GET /` search, `GET /visit/{visit_id}`, `GET /patient/{patient_id}` —
// no update/submit-for-review/sign/lock endpoints exist yet, even though
// the domain entity itself supports all four lifecycle transitions).
//
// Field names are grounded in the real domain entity
// (`app.modules.clinical_notes.domain.entities.ClinicalNote`):
// `patient_id, visit_id, doctor_id, note_number, note_type,
// encounter_datetime, status, chief_complaint_summary, history_summary,
// examination_summary, assessment_summary, plan_summary, ai_generated,
// ai_model, ai_version, signature (signed_at/signed_by), locked_at`.
// `ClinicalNoteType`/`ClinicalNoteStatus` match `domain/enums.py`
// verbatim.
//
// Status workflow is grounded in the real entity's own guards, not
// invented: `draft → in_review → signed → locked` is linear with no
// reverse path, and — critically — `_ensure_editable()` (which backs
// `update_details()`) only allows edits while `status is DRAFT`. This
// mock's `updateClinicalNote()` enforces the exact same rule
// (`isClinicalNoteEditable()`), and the Edit page
// (`ClinicalNoteEditContent`) refuses to render the form for a
// non-editable note — matching real behavior instead of silently
// allowing an edit the real API would reject. `lock()` has no
// application-layer use case wired up at all yet, so this UI never
// offers a "Lock" action — only "Save as Draft" and "Save & Sign"
// (mirroring `sign()`, which the domain method *does* allow from DRAFT
// directly, even though no use case calls it yet either — a reasonable
// forward-compatible UI given the domain already supports it).
//
// Three sub-resource shapes (`SOAPNote`, `VisitDiagnosis`,
// `VisitPrescription`/`PrescriptionItem`) are imported from
// `lib/mock/visits.ts` rather than redeclared — they represent the exact
// same real backend entities (SOAP Notes, Diagnosis, Prescriptions),
// just looked up here by `clinical_note_id`/`visit_id` instead of
// `visit_id` alone. `VisitDocument` is reused the same way for
// "Attachments Summary": the real backend has no clinical-note-specific
// attachment entity at all — `VisitAttachment` is keyed strictly by
// `visit_id` — so a clinical note's attachments are really its parent
// visit's attachments.
//
// `patient_name`/`patient_number`/`doctor_name`/`visit_number` are
// denormalized display fields, same reasoning as every other mock
// repository in this app. `created_by_name`/`updated_by_name`/
// `signed_by_name` are similarly denormalized (the real API returns
// `signed_by: UUID`, not a name).

import type { PaginatedResponse } from "@/types";
import type { SOAPNote, VisitDiagnosis, VisitDocument, VisitPrescription } from "@/lib/mock/visits";

const MIN_LATENCY_MS = 350;

function mockFetch<T>(value: T, latencyMs: number = MIN_LATENCY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), latencyMs));
}

function generateId(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

// --- Enums (verbatim from `app.modules.clinical_notes.domain.enums`) --

export type ClinicalNoteType = "initial" | "follow_up" | "emergency" | "consultation" | "discharge";
export type ClinicalNoteStatus = "draft" | "in_review" | "signed" | "locked";

export const CLINICAL_NOTE_TYPE_OPTIONS: { label: string; value: ClinicalNoteType }[] = [
  { label: "Initial", value: "initial" },
  { label: "Follow-up", value: "follow_up" },
  { label: "Emergency", value: "emergency" },
  { label: "Consultation", value: "consultation" },
  { label: "Discharge", value: "discharge" },
];

export const CLINICAL_NOTE_STATUS_OPTIONS: { label: string; value: ClinicalNoteStatus }[] = [
  { label: "Draft", value: "draft" },
  { label: "In Review", value: "in_review" },
  { label: "Signed", value: "signed" },
  { label: "Locked", value: "locked" },
];

export function getClinicalNoteTypeLabel(type: ClinicalNoteType): string {
  return CLINICAL_NOTE_TYPE_OPTIONS.find((option) => option.value === type)?.label ?? type;
}

export function getClinicalNoteStatusLabel(status: ClinicalNoteStatus): string {
  return CLINICAL_NOTE_STATUS_OPTIONS.find((option) => option.value === status)?.label ?? status;
}

// Mirrors `ClinicalNote._ensure_editable()` exactly: only a draft note
// can have its own content (`update_details()`) modified.
export function isClinicalNoteEditable(status: ClinicalNoteStatus): boolean {
  return status === "draft";
}

// --- Templates ----------------------------------------------------------
// UI-only content (not a real backend concept) for the "Templates"
// feature of the create/edit form — static configuration, not seed
// business data, so it lives alongside the other exported option arrays
// rather than inside a component.

export interface ClinicalNoteTemplate {
  id: string;
  label: string;
  chief_complaint_summary: string;
  history_summary: string;
  examination_summary: string;
  assessment_summary: string;
  plan_summary: string;
}

export const CLINICAL_NOTE_TEMPLATES: ClinicalNoteTemplate[] = [
  {
    id: "general-followup",
    label: "General Follow-up",
    chief_complaint_summary: "Follow-up visit for ongoing condition management.",
    history_summary:
      "Patient reports symptoms are stable since the last visit, with no new concerns raised.",
    examination_summary: "Vitals within normal limits. No acute distress. Exam unremarkable.",
    assessment_summary: "Condition stable on current management plan.",
    plan_summary: "Continue current treatment. Follow up in 3 months, sooner if symptoms worsen.",
  },
  {
    id: "new-patient-intake",
    label: "New Patient Intake",
    chief_complaint_summary: "New patient establishing care.",
    history_summary: "Reviewed past medical, surgical, family, and social history with patient.",
    examination_summary: "Full physical examination performed, findings documented below.",
    assessment_summary: "No acute concerns identified at this visit.",
    plan_summary: "Order baseline labs. Schedule follow-up to review results.",
  },
  {
    id: "acute-illness",
    label: "Acute Illness Visit",
    chief_complaint_summary: "Acute onset of symptoms, patient presenting for evaluation.",
    history_summary: "Symptom onset, duration, and severity reviewed with patient.",
    examination_summary: "Focused examination performed relevant to presenting complaint.",
    assessment_summary: "Likely acute, self-limited process; findings consistent with history.",
    plan_summary:
      "Symptomatic treatment recommended. Return if symptoms worsen or persist beyond 7 days.",
  },
];

// --- Core shapes ---------------------------------------------------------

export interface ClinicalNote {
  clinical_note_id: string;
  organization_id: string;
  note_number: string;
  patient_id: string;
  patient_name: string;
  patient_number: string;
  doctor_id: string;
  doctor_name: string;
  visit_id: string;
  visit_number: string;
  note_type: ClinicalNoteType;
  status: ClinicalNoteStatus;
  encounter_datetime: string; // ISO 8601
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
}

export interface ClinicalNoteDetail extends ClinicalNote {
  chief_complaint_summary: string | null;
  history_summary: string | null;
  examination_summary: string | null;
  assessment_summary: string | null;
  plan_summary: string | null;
  ai_generated: boolean;
  ai_model: string | null;
  ai_version: string | null;
  signed_at: string | null;
  signed_by_name: string | null;
  locked_at: string | null;
  created_by_name: string;
  updated_by_name: string;
  soap_note: SOAPNote | null;
  diagnoses: VisitDiagnosis[];
  prescription: VisitPrescription | null;
  attachments: VisitDocument[];
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

interface ClinicalNoteSeed {
  visit_id: string;
  visit_number: string;
  patient_id: string;
  patient_name: string;
  patient_number: string;
  doctor_id: string;
  doctor_name: string;
  dayOffset: number;
  nominalTime: string;
  note_type: ClinicalNoteType;
  status: ClinicalNoteStatus;
  rich?: boolean;
}

const SEED: ClinicalNoteSeed[] = [
  {
    visit_id: "vis8-0001",
    visit_number: "VIS-80001",
    patient_id: "pat-0001",
    patient_name: "Michael Chen",
    patient_number: "PAT-100001",
    doctor_id: "doc-0001",
    doctor_name: "Dr. Amara Okafor",
    dayOffset: 0,
    nominalTime: "09:00",
    note_type: "consultation",
    status: "locked",
    rich: true,
  },
  {
    visit_id: "vis8-0002",
    visit_number: "VIS-80002",
    patient_id: "pat-0002",
    patient_name: "Sarah Johnson",
    patient_number: "PAT-100002",
    doctor_id: "doc-0001",
    doctor_name: "Dr. Amara Okafor",
    dayOffset: 0,
    nominalTime: "09:30",
    note_type: "follow_up",
    status: "signed",
    rich: true,
  },
  {
    visit_id: "vis8-0003",
    visit_number: "VIS-80003",
    patient_id: "pat-0004",
    patient_name: "David Kim",
    patient_number: "PAT-100004",
    doctor_id: "doc-0002",
    doctor_name: "Dr. Daniel Reyes",
    dayOffset: -1,
    nominalTime: "10:00",
    note_type: "consultation",
    status: "signed",
    rich: true,
  },
  {
    visit_id: "vis8-0004",
    visit_number: "VIS-80004",
    patient_id: "pat-0003",
    patient_name: "Amara Nwosu",
    patient_number: "PAT-100003",
    doctor_id: "doc-0001",
    doctor_name: "Dr. Amara Okafor",
    dayOffset: -2,
    nominalTime: "14:00",
    note_type: "follow_up",
    status: "locked",
    rich: true,
  },
  {
    visit_id: "vis8-0005",
    visit_number: "VIS-80005",
    patient_id: "pat-0006",
    patient_name: "James Williams",
    patient_number: "PAT-100006",
    doctor_id: "doc-0004",
    doctor_name: "Dr. Marcus Webb",
    dayOffset: -3,
    nominalTime: "13:00",
    note_type: "consultation",
    status: "in_review",
  },
  {
    visit_id: "vis8-0006",
    visit_number: "VIS-80006",
    patient_id: "pat-0011",
    patient_name: "Robert Lee",
    patient_number: "PAT-100011",
    doctor_id: "doc-0004",
    doctor_name: "Dr. Marcus Webb",
    dayOffset: -1,
    nominalTime: "15:00",
    note_type: "follow_up",
    status: "draft",
  },
  {
    visit_id: "vis8-0007",
    visit_number: "VIS-80007",
    patient_id: "pat-0013",
    patient_name: "Noah Thompson",
    patient_number: "PAT-100013",
    doctor_id: "doc-0001",
    doctor_name: "Dr. Amara Okafor",
    dayOffset: -4,
    nominalTime: "11:00",
    note_type: "follow_up",
    status: "signed",
  },
  {
    visit_id: "vis8-0008",
    visit_number: "VIS-80008",
    patient_id: "pat-0016",
    patient_name: "Sofia Torres",
    patient_number: "PAT-100016",
    doctor_id: "doc-0005",
    doctor_name: "Dr. Hannah Kim",
    dayOffset: -6,
    nominalTime: "13:30",
    note_type: "consultation",
    status: "draft",
  },
  {
    visit_id: "vis8-0009",
    visit_number: "VIS-80009",
    patient_id: "pat-0014",
    patient_name: "Ava Rodriguez",
    patient_number: "PAT-100014",
    doctor_id: "doc-0003",
    doctor_name: "Dr. Priya Sharma",
    dayOffset: -10,
    nominalTime: "09:00",
    note_type: "initial",
    status: "in_review",
  },
  {
    visit_id: "vis8-0010",
    visit_number: "VIS-80010",
    patient_id: "pat-0008",
    patient_name: "Ethan Brown",
    patient_number: "PAT-100008",
    doctor_id: "doc-0001",
    doctor_name: "Dr. Amara Okafor",
    dayOffset: 0,
    nominalTime: "10:30",
    note_type: "follow_up",
    status: "draft",
  },
];

function buildRichSubResources(seed: ClinicalNoteSeed): {
  soap_note: SOAPNote | null;
  diagnoses: VisitDiagnosis[];
  prescription: VisitPrescription | null;
  attachments: VisitDocument[];
} {
  if (!seed.rich) {
    return { soap_note: null, diagnoses: [], prescription: null, attachments: [] };
  }

  const recordedAt = atTime(dateOffset(seed.dayOffset), seed.nominalTime);

  return {
    soap_note: {
      chief_complaint: "Routine follow-up, no new complaints reported.",
      history_of_present_illness:
        "Symptoms gradual in onset over the past two weeks, no prior similar episodes.",
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
      prescription_number: `RX-${71000 + Math.floor(Math.random() * 999)}`,
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
    attachments: [
      {
        document_id: generateId("doc"),
        file_name: `Encounter_Summary_${dateOffset(seed.dayOffset)}.pdf`,
        attachment_type: "pdf",
        mime_type: "application/pdf",
        file_size_bytes: 198_000,
        uploaded_at: recordedAt.toISOString(),
        description: "Encounter summary and after-visit instructions.",
      },
    ],
  };
}

let clinicalNotes: ClinicalNoteDetail[] = SEED.map((seed, index) => {
  const num = index + 1;
  const clinical_note_id = `cn-${String(num).padStart(4, "0")}`;
  const encounterDate = dateOffset(seed.dayOffset);
  const encounterAt = atTime(encounterDate, seed.nominalTime);
  const createdAt = new Date(encounterAt.getTime() + 20 * 60_000);
  const signedAt =
    seed.status === "signed" || seed.status === "locked"
      ? new Date(createdAt.getTime() + 2 * 24 * 60 * 60_000)
      : null;
  const lockedAt =
    seed.status === "locked" && signedAt
      ? new Date(signedAt.getTime() + 5 * 24 * 60 * 60_000)
      : null;
  const updatedAt = lockedAt ?? signedAt ?? createdAt;

  const subResources = buildRichSubResources(seed);

  return {
    clinical_note_id,
    organization_id: ORG_ID,
    note_number: `CN-${70000 + num}`,
    patient_id: seed.patient_id,
    patient_name: seed.patient_name,
    patient_number: seed.patient_number,
    doctor_id: seed.doctor_id,
    doctor_name: seed.doctor_name,
    visit_id: seed.visit_id,
    visit_number: seed.visit_number,
    note_type: seed.note_type,
    status: seed.status,
    encounter_datetime: encounterAt.toISOString(),
    created_at: createdAt.toISOString(),
    updated_at: updatedAt.toISOString(),
    chief_complaint_summary: seed.rich
      ? "Routine follow-up, no new complaints reported."
      : "Follow-up visit.",
    history_summary: seed.rich
      ? "Symptoms gradual in onset over the past two weeks, no prior similar episodes."
      : null,
    examination_summary: seed.rich
      ? "Alert and oriented. Heart and lung sounds normal. No acute distress observed."
      : null,
    assessment_summary: seed.rich
      ? "Stable, consistent with chronic condition management; no new concerns identified."
      : null,
    plan_summary: seed.rich
      ? "Continue current treatment plan, follow up in 3 months, patient education provided."
      : null,
    ai_generated: false,
    ai_model: null,
    ai_version: null,
    signed_at: signedAt ? signedAt.toISOString() : null,
    signed_by_name: signedAt ? seed.doctor_name : null,
    locked_at: lockedAt ? lockedAt.toISOString() : null,
    created_by_name: seed.doctor_name,
    updated_by_name: seed.doctor_name,
    ...subResources,
  };
});

// --- Repository: reads -----------------------------------------------

export interface ClinicalNoteListParams {
  search?: string;
  status?: ClinicalNoteStatus | "all";
  noteType?: ClinicalNoteType | "all";
  sortBy?: "note_number" | "patient_name" | "doctor_name" | "created_at" | "updated_at" | "status";
  sortDirection?: "asc" | "desc";
  page?: number;
  pageSize?: number;
}

function matchesSearch(note: ClinicalNote, search: string): boolean {
  const needle = search.trim().toLowerCase();
  if (!needle) return true;
  return (
    note.note_number.toLowerCase().includes(needle) ||
    note.patient_name.toLowerCase().includes(needle) ||
    note.doctor_name.toLowerCase().includes(needle) ||
    note.visit_number.toLowerCase().includes(needle)
  );
}

function sortKey(
  note: ClinicalNote,
  sortBy: NonNullable<ClinicalNoteListParams["sortBy"]>,
): string {
  return String(note[sortBy]);
}

function stripDetail(note: ClinicalNoteDetail): ClinicalNote {
  return {
    clinical_note_id: note.clinical_note_id,
    organization_id: note.organization_id,
    note_number: note.note_number,
    patient_id: note.patient_id,
    patient_name: note.patient_name,
    patient_number: note.patient_number,
    doctor_id: note.doctor_id,
    doctor_name: note.doctor_name,
    visit_id: note.visit_id,
    visit_number: note.visit_number,
    note_type: note.note_type,
    status: note.status,
    encounter_datetime: note.encounter_datetime,
    created_at: note.created_at,
    updated_at: note.updated_at,
  };
}

export function listClinicalNotes(
  params: ClinicalNoteListParams = {},
): Promise<PaginatedResponse<ClinicalNote>> {
  const {
    search = "",
    status = "all",
    noteType = "all",
    sortBy = "created_at",
    sortDirection = "desc",
    page = 1,
    pageSize = 10,
  } = params;

  let filtered = clinicalNotes.filter((note) => matchesSearch(note, search));
  if (status !== "all") {
    filtered = filtered.filter((note) => note.status === status);
  }
  if (noteType !== "all") {
    filtered = filtered.filter((note) => note.note_type === noteType);
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

export function getClinicalNote(clinicalNoteId: string): Promise<ClinicalNoteDetail | null> {
  const found = clinicalNotes.find((note) => note.clinical_note_id === clinicalNoteId) ?? null;
  return mockFetch(found, 300);
}

// --- Repository: writes -------------------------------------------------
// Deliberately the same field set the real `CreateClinicalNoteRequest`
// accepts — see this file's own docstring. `status` is never client-set
// on create (every new note starts `draft`, matching the real API).

export interface ClinicalNoteFormInput {
  patient_id: string;
  visit_id: string;
  doctor_id: string;
  note_type: ClinicalNoteType;
  encounter_datetime: string;
  chief_complaint_summary: string;
  history_summary: string;
  examination_summary: string;
  assessment_summary: string;
  plan_summary: string;
}

function resolveDisplay(input: { patient_id: string; doctor_id: string; visit_id: string }): {
  patient_name: string;
  patient_number: string;
  doctor_name: string;
  visit_number: string;
} {
  const existing = clinicalNotes.find(
    (note) =>
      note.patient_id === input.patient_id ||
      note.doctor_id === input.doctor_id ||
      note.visit_id === input.visit_id,
  );
  return {
    patient_name:
      existing?.patient_id === input.patient_id ? existing.patient_name : "Unknown Patient",
    patient_number: existing?.patient_id === input.patient_id ? existing.patient_number : "—",
    doctor_name: existing?.doctor_id === input.doctor_id ? existing.doctor_name : "Unknown Doctor",
    visit_number: existing?.visit_id === input.visit_id ? existing.visit_number : "—",
  };
}

export async function createClinicalNote(
  input: ClinicalNoteFormInput,
): Promise<ClinicalNoteDetail> {
  const id = generateId("cn");
  const nextNumber = 70000 + clinicalNotes.length + 1;
  const display = resolveDisplay(input);
  const now = new Date().toISOString();

  const created: ClinicalNoteDetail = {
    clinical_note_id: id,
    organization_id: ORG_ID,
    note_number: `CN-${nextNumber}`,
    patient_id: input.patient_id,
    patient_name: display.patient_name,
    patient_number: display.patient_number,
    doctor_id: input.doctor_id,
    doctor_name: display.doctor_name,
    visit_id: input.visit_id,
    visit_number: display.visit_number,
    note_type: input.note_type,
    status: "draft",
    encounter_datetime: input.encounter_datetime,
    created_at: now,
    updated_at: now,
    chief_complaint_summary: input.chief_complaint_summary || null,
    history_summary: input.history_summary || null,
    examination_summary: input.examination_summary || null,
    assessment_summary: input.assessment_summary || null,
    plan_summary: input.plan_summary || null,
    ai_generated: false,
    ai_model: null,
    ai_version: null,
    signed_at: null,
    signed_by_name: null,
    locked_at: null,
    created_by_name: display.doctor_name,
    updated_by_name: display.doctor_name,
    soap_note: null,
    diagnoses: [],
    prescription: null,
    attachments: [],
  };

  clinicalNotes = [created, ...clinicalNotes];
  return mockFetch(created, 500);
}

export async function updateClinicalNote(
  clinicalNoteId: string,
  input: ClinicalNoteFormInput,
  action: "draft" | "sign" = "draft",
): Promise<ClinicalNoteDetail> {
  const index = clinicalNotes.findIndex((note) => note.clinical_note_id === clinicalNoteId);
  const existing = clinicalNotes[index];
  if (!existing) {
    throw new Error(`Clinical note ${clinicalNoteId} not found`);
  }
  if (!isClinicalNoteEditable(existing.status)) {
    throw new Error(`Clinical note ${clinicalNoteId} is not editable in its current status`);
  }

  const display = resolveDisplay(input);
  const now = new Date().toISOString();

  const updated: ClinicalNoteDetail = {
    ...existing,
    patient_id: input.patient_id,
    patient_name:
      input.patient_id === existing.patient_id ? existing.patient_name : display.patient_name,
    patient_number:
      input.patient_id === existing.patient_id ? existing.patient_number : display.patient_number,
    doctor_id: input.doctor_id,
    doctor_name:
      input.doctor_id === existing.doctor_id ? existing.doctor_name : display.doctor_name,
    visit_id: input.visit_id,
    visit_number:
      input.visit_id === existing.visit_id ? existing.visit_number : display.visit_number,
    note_type: input.note_type,
    encounter_datetime: input.encounter_datetime,
    updated_at: now,
    chief_complaint_summary: input.chief_complaint_summary || null,
    history_summary: input.history_summary || null,
    examination_summary: input.examination_summary || null,
    assessment_summary: input.assessment_summary || null,
    plan_summary: input.plan_summary || null,
    status: action === "sign" ? "signed" : existing.status,
    signed_at: action === "sign" ? now : existing.signed_at,
    signed_by_name: action === "sign" ? existing.doctor_name : existing.signed_by_name,
  };

  clinicalNotes = [...clinicalNotes.slice(0, index), updated, ...clinicalNotes.slice(index + 1)];
  return mockFetch(updated, 500);
}

export function clinicalNoteToFormInput(note: ClinicalNoteDetail): ClinicalNoteFormInput {
  return {
    patient_id: note.patient_id,
    visit_id: note.visit_id,
    doctor_id: note.doctor_id,
    note_type: note.note_type,
    encounter_datetime: note.encounter_datetime.slice(0, 16),
    chief_complaint_summary: note.chief_complaint_summary ?? "",
    history_summary: note.history_summary ?? "",
    examination_summary: note.examination_summary ?? "",
    assessment_summary: note.assessment_summary ?? "",
    plan_summary: note.plan_summary ?? "",
  };
}
