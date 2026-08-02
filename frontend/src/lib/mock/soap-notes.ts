// Temporary frontend mock repository for SOAP Notes Management
// (`app/(dashboard)/dashboard/soap-notes/*`). No backend API is consumed
// anywhere in this module — every function below reads from and writes
// to an in-memory array, standing in for the backend SOAP Notes module
// (`app.modules.soap_notes`).
//
// Field names are grounded in the real domain entity
// (`app.modules.soap_notes.domain.entities.SOAPNote`), a one-to-one
// child of `ClinicalNote`: `clinical_note_id, patient_id, visit_id,
// doctor_id, chief_complaint, history_of_present_illness,
// review_of_systems, physical_examination, vital_sign_summary,
// assessment, plan`. The real entity's four identity FKs are all
// derived server-side from the parent `ClinicalNote`, never
// independently caller-supplied — this mock's create/update functions
// mirror that by deriving `patient_id`/`doctor_id`/`clinical_note_id`
// from the selected visit rather than accepting them as free-standing
// input (see `SOAPNoteFormInput` below and
// `features/soap-notes/components/soap-note-form.tsx`'s auto-sync
// effect).
//
// Two deliberate simplifications relative to the real entity, both
// called out because they don't map to anything real:
//   - `subjective`/`objective`/`assessment`/`plan` — the real entity
//     splits Subjective into `chief_complaint` +
//     `history_of_present_illness` + `review_of_systems`, and Objective
//     into `physical_examination` + `vital_sign_summary` (7 fields
//     total). This module's Create form explicitly asks for exactly
//     "4 editors" (Subjective/Objective/Assessment/Plan), so this mock
//     collapses each SOAP quadrant into one free-text field instead of
//     preserving the finer 7-field split — the same real-world content,
//     simplified to match what the UI actually asks the clinician to
//     fill in.
//   - `status` (`SOAPNoteStatus`) — the real entity has **no status
//     field of its own at all**; editability is governed entirely by
//     the parent `ClinicalNote.status` (`is_editable()` on the public
//     query port returns true for Draft/In Review, false for
//     Signed/Locked). Since this module's Create/Edit forms explicitly
//     ask for a "Draft / Final status" the clinician sets directly
//     (mirroring `lib/mock/clinical-notes.ts`'s own Draft/Sign UX,
//     without needing to cross-mutate that module's separate in-memory
//     array), this mock gives the SOAP note its own simple two-state
//     field instead. `isSoapNoteEditable()` gates editing on it exactly
//     the way the real parent-status check would.
//
// `patient_name`/`patient_number`/`doctor_name`/`visit_number`/
// `clinical_note_number` are denormalized display fields, same
// reasoning as every other mock repository in this app. `diagnoses`
// (`VisitDiagnosis[]`) and `prescription` (`VisitPrescription`) reuse
// the exact same real sub-entity shapes already modeled in
// `lib/mock/visits.ts` (Diagnosis is keyed by `visit_id`, Prescription
// by `clinical_note_id` — both genuinely apply to a SOAP note's parent
// visit/clinical note) rather than being redeclared here.

import type { PaginatedResponse } from "@/types";
import type { VisitDiagnosis, VisitPrescription } from "@/lib/mock/visits";

const MIN_LATENCY_MS = 350;

function mockFetch<T>(value: T, latencyMs: number = MIN_LATENCY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), latencyMs));
}

function generateId(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

// --- Status (frontend-only — see this file's own docstring) -----------

export type SOAPNoteStatus = "draft" | "final";

export const SOAP_NOTE_STATUS_OPTIONS: { label: string; value: SOAPNoteStatus }[] = [
  { label: "Draft", value: "draft" },
  { label: "Final", value: "final" },
];

export function getSoapNoteStatusLabel(status: SOAPNoteStatus): string {
  return SOAP_NOTE_STATUS_OPTIONS.find((option) => option.value === status)?.label ?? status;
}

// Mirrors the real cross-module contract in spirit
// (`ClinicalNoteQueryService.is_editable()`): only a draft can be
// changed further.
export function isSoapNoteEditable(status: SOAPNoteStatus): boolean {
  return status === "draft";
}

// --- Core shapes ---------------------------------------------------------

export interface SOAPNote {
  soap_note_id: string;
  organization_id: string;
  soap_number: string;
  clinical_note_id: string;
  clinical_note_number: string;
  patient_id: string;
  patient_name: string;
  patient_number: string;
  doctor_id: string;
  doctor_name: string;
  visit_id: string;
  visit_number: string;
  status: SOAPNoteStatus;
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
}

export interface SOAPNoteDetail extends SOAPNote {
  subjective: string | null;
  objective: string | null;
  assessment: string | null;
  plan: string | null;
  created_by_name: string;
  updated_by_name: string;
  diagnoses: VisitDiagnosis[];
  prescription: VisitPrescription | null;
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

interface SoapNoteSeed {
  clinical_note_id: string;
  clinical_note_number: string;
  visit_id: string;
  visit_number: string;
  patient_id: string;
  patient_name: string;
  patient_number: string;
  doctor_id: string;
  doctor_name: string;
  dayOffset: number;
  nominalTime: string;
  status: SOAPNoteStatus;
  rich?: boolean;
}

const SEED: SoapNoteSeed[] = [
  {
    clinical_note_id: "cn-0001",
    clinical_note_number: "CN-70001",
    visit_id: "vis8-0001",
    visit_number: "VIS-80001",
    patient_id: "pat-0001",
    patient_name: "Michael Chen",
    patient_number: "PAT-100001",
    doctor_id: "doc-0001",
    doctor_name: "Dr. Amara Okafor",
    dayOffset: 0,
    nominalTime: "09:00",
    status: "final",
    rich: true,
  },
  {
    clinical_note_id: "cn-0002",
    clinical_note_number: "CN-70002",
    visit_id: "vis8-0002",
    visit_number: "VIS-80002",
    patient_id: "pat-0002",
    patient_name: "Sarah Johnson",
    patient_number: "PAT-100002",
    doctor_id: "doc-0001",
    doctor_name: "Dr. Amara Okafor",
    dayOffset: 0,
    nominalTime: "09:30",
    status: "final",
    rich: true,
  },
  {
    clinical_note_id: "cn-0003",
    clinical_note_number: "CN-70003",
    visit_id: "vis8-0003",
    visit_number: "VIS-80003",
    patient_id: "pat-0004",
    patient_name: "David Kim",
    patient_number: "PAT-100004",
    doctor_id: "doc-0002",
    doctor_name: "Dr. Daniel Reyes",
    dayOffset: -1,
    nominalTime: "10:00",
    status: "final",
    rich: true,
  },
  {
    clinical_note_id: "cn-0004",
    clinical_note_number: "CN-70004",
    visit_id: "vis8-0004",
    visit_number: "VIS-80004",
    patient_id: "pat-0003",
    patient_name: "Amara Nwosu",
    patient_number: "PAT-100003",
    doctor_id: "doc-0001",
    doctor_name: "Dr. Amara Okafor",
    dayOffset: -2,
    nominalTime: "14:00",
    status: "final",
    rich: true,
  },
  {
    clinical_note_id: "cn-0005",
    clinical_note_number: "CN-70005",
    visit_id: "vis8-0005",
    visit_number: "VIS-80005",
    patient_id: "pat-0006",
    patient_name: "James Williams",
    patient_number: "PAT-100006",
    doctor_id: "doc-0004",
    doctor_name: "Dr. Marcus Webb",
    dayOffset: -3,
    nominalTime: "13:00",
    status: "draft",
  },
  {
    clinical_note_id: "cn-0006",
    clinical_note_number: "CN-70006",
    visit_id: "vis8-0006",
    visit_number: "VIS-80006",
    patient_id: "pat-0011",
    patient_name: "Robert Lee",
    patient_number: "PAT-100011",
    doctor_id: "doc-0004",
    doctor_name: "Dr. Marcus Webb",
    dayOffset: -1,
    nominalTime: "15:00",
    status: "draft",
  },
  {
    clinical_note_id: "cn-0007",
    clinical_note_number: "CN-70007",
    visit_id: "vis8-0007",
    visit_number: "VIS-80007",
    patient_id: "pat-0013",
    patient_name: "Noah Thompson",
    patient_number: "PAT-100013",
    doctor_id: "doc-0001",
    doctor_name: "Dr. Amara Okafor",
    dayOffset: -4,
    nominalTime: "11:00",
    status: "final",
  },
  {
    clinical_note_id: "cn-0008",
    clinical_note_number: "CN-70008",
    visit_id: "vis8-0008",
    visit_number: "VIS-80008",
    patient_id: "pat-0016",
    patient_name: "Sofia Torres",
    patient_number: "PAT-100016",
    doctor_id: "doc-0005",
    doctor_name: "Dr. Hannah Kim",
    dayOffset: -6,
    nominalTime: "13:30",
    status: "draft",
  },
  {
    clinical_note_id: "cn-0009",
    clinical_note_number: "CN-70009",
    visit_id: "vis8-0009",
    visit_number: "VIS-80009",
    patient_id: "pat-0014",
    patient_name: "Ava Rodriguez",
    patient_number: "PAT-100014",
    doctor_id: "doc-0003",
    doctor_name: "Dr. Priya Sharma",
    dayOffset: -10,
    nominalTime: "09:00",
    status: "draft",
  },
  {
    clinical_note_id: "cn-0010",
    clinical_note_number: "CN-70010",
    visit_id: "vis8-0010",
    visit_number: "VIS-80010",
    patient_id: "pat-0008",
    patient_name: "Ethan Brown",
    patient_number: "PAT-100008",
    doctor_id: "doc-0001",
    doctor_name: "Dr. Amara Okafor",
    dayOffset: 0,
    nominalTime: "10:30",
    status: "draft",
  },
];

function buildRichSubResources(seed: SoapNoteSeed): {
  diagnoses: VisitDiagnosis[];
  prescription: VisitPrescription | null;
} {
  if (!seed.rich) {
    return { diagnoses: [], prescription: null };
  }

  const recordedAt = atTime(dateOffset(seed.dayOffset), seed.nominalTime);

  return {
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
      prescription_number: `RX-${72000 + Math.floor(Math.random() * 999)}`,
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
  };
}

let soapNotes: SOAPNoteDetail[] = SEED.map((seed, index) => {
  const num = index + 1;
  const soap_note_id = `soap-${String(num).padStart(4, "0")}`;
  const recordedAt = atTime(dateOffset(seed.dayOffset), seed.nominalTime);
  const createdAt = new Date(recordedAt.getTime() + 25 * 60_000);
  const updatedAt =
    seed.status === "final" ? new Date(createdAt.getTime() + 60 * 60_000) : createdAt;

  const subResources = buildRichSubResources(seed);

  return {
    soap_note_id,
    organization_id: ORG_ID,
    soap_number: `SOAP-${90000 + num}`,
    clinical_note_id: seed.clinical_note_id,
    clinical_note_number: seed.clinical_note_number,
    patient_id: seed.patient_id,
    patient_name: seed.patient_name,
    patient_number: seed.patient_number,
    doctor_id: seed.doctor_id,
    doctor_name: seed.doctor_name,
    visit_id: seed.visit_id,
    visit_number: seed.visit_number,
    status: seed.status,
    created_at: createdAt.toISOString(),
    updated_at: updatedAt.toISOString(),
    subjective: seed.rich
      ? "Patient reports gradual onset of symptoms over the past two weeks, no prior similar episodes. No fever, chest pain, or shortness of breath."
      : "Routine follow-up, no new complaints reported.",
    objective: seed.rich
      ? "Vitals stable (T 36.8°C, HR 74, RR 16, BP 126/80, SpO2 98%). Alert and oriented. Heart and lung sounds normal. No acute distress observed."
      : null,
    assessment: seed.rich
      ? "Stable, consistent with chronic condition management; no new concerns identified."
      : null,
    plan: seed.rich
      ? "Continue current treatment plan, follow up in 3 months, patient education provided."
      : null,
    created_by_name: seed.doctor_name,
    updated_by_name: seed.doctor_name,
    ...subResources,
  };
});

// --- Repository: reads -----------------------------------------------

export interface SOAPNoteListParams {
  search?: string;
  status?: SOAPNoteStatus | "all";
  sortBy?: "soap_number" | "patient_name" | "doctor_name" | "created_at" | "status";
  sortDirection?: "asc" | "desc";
  page?: number;
  pageSize?: number;
}

function matchesSearch(note: SOAPNote, search: string): boolean {
  const needle = search.trim().toLowerCase();
  if (!needle) return true;
  return (
    note.soap_number.toLowerCase().includes(needle) ||
    note.patient_name.toLowerCase().includes(needle) ||
    note.doctor_name.toLowerCase().includes(needle) ||
    note.visit_number.toLowerCase().includes(needle)
  );
}

function sortKey(note: SOAPNote, sortBy: NonNullable<SOAPNoteListParams["sortBy"]>): string {
  return String(note[sortBy]);
}

function stripDetail(note: SOAPNoteDetail): SOAPNote {
  return {
    soap_note_id: note.soap_note_id,
    organization_id: note.organization_id,
    soap_number: note.soap_number,
    clinical_note_id: note.clinical_note_id,
    clinical_note_number: note.clinical_note_number,
    patient_id: note.patient_id,
    patient_name: note.patient_name,
    patient_number: note.patient_number,
    doctor_id: note.doctor_id,
    doctor_name: note.doctor_name,
    visit_id: note.visit_id,
    visit_number: note.visit_number,
    status: note.status,
    created_at: note.created_at,
    updated_at: note.updated_at,
  };
}

export function listSoapNotes(
  params: SOAPNoteListParams = {},
): Promise<PaginatedResponse<SOAPNote>> {
  const {
    search = "",
    status = "all",
    sortBy = "created_at",
    sortDirection = "desc",
    page = 1,
    pageSize = 10,
  } = params;

  let filtered = soapNotes.filter((note) => matchesSearch(note, search));
  if (status !== "all") {
    filtered = filtered.filter((note) => note.status === status);
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

export function getSoapNote(soapNoteId: string): Promise<SOAPNoteDetail | null> {
  const found = soapNotes.find((note) => note.soap_note_id === soapNoteId) ?? null;
  return mockFetch(found, 300);
}

// --- Repository: writes -------------------------------------------------
// `patient_id`/`doctor_id`/`clinical_note_id` are deliberately absent
// from this input shape — mirroring the real entity, they're derived
// from the selected visit, not independently supplied. See this file's
// own docstring.

export interface SOAPNoteFormInput {
  patient_id: string;
  visit_id: string;
  doctor_id: string;
  clinical_note_id: string;
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
}

function resolveDisplay(input: {
  patient_id: string;
  doctor_id: string;
  visit_id: string;
  clinical_note_id: string;
}): {
  patient_name: string;
  patient_number: string;
  doctor_name: string;
  visit_number: string;
  clinical_note_number: string;
} {
  const existing = soapNotes.find(
    (note) =>
      note.patient_id === input.patient_id ||
      note.doctor_id === input.doctor_id ||
      note.visit_id === input.visit_id ||
      note.clinical_note_id === input.clinical_note_id,
  );
  return {
    patient_name:
      existing?.patient_id === input.patient_id ? existing.patient_name : "Unknown Patient",
    patient_number: existing?.patient_id === input.patient_id ? existing.patient_number : "—",
    doctor_name: existing?.doctor_id === input.doctor_id ? existing.doctor_name : "Unknown Doctor",
    visit_number: existing?.visit_id === input.visit_id ? existing.visit_number : "—",
    clinical_note_number:
      existing?.clinical_note_id === input.clinical_note_id ? existing.clinical_note_number : "—",
  };
}

export async function createSoapNote(
  input: SOAPNoteFormInput,
  status: SOAPNoteStatus,
): Promise<SOAPNoteDetail> {
  const id = generateId("soap");
  const nextNumber = 90000 + soapNotes.length + 1;
  const display = resolveDisplay(input);
  const now = new Date().toISOString();

  const created: SOAPNoteDetail = {
    soap_note_id: id,
    organization_id: ORG_ID,
    soap_number: `SOAP-${nextNumber}`,
    clinical_note_id: input.clinical_note_id,
    clinical_note_number: display.clinical_note_number,
    patient_id: input.patient_id,
    patient_name: display.patient_name,
    patient_number: display.patient_number,
    doctor_id: input.doctor_id,
    doctor_name: display.doctor_name,
    visit_id: input.visit_id,
    visit_number: display.visit_number,
    status,
    created_at: now,
    updated_at: now,
    subjective: input.subjective || null,
    objective: input.objective || null,
    assessment: input.assessment || null,
    plan: input.plan || null,
    created_by_name: display.doctor_name,
    updated_by_name: display.doctor_name,
    diagnoses: [],
    prescription: null,
  };

  soapNotes = [created, ...soapNotes];
  return mockFetch(created, 500);
}

export async function updateSoapNote(
  soapNoteId: string,
  input: SOAPNoteFormInput,
  status: SOAPNoteStatus,
): Promise<SOAPNoteDetail> {
  const index = soapNotes.findIndex((note) => note.soap_note_id === soapNoteId);
  const existing = soapNotes[index];
  if (!existing) {
    throw new Error(`SOAP note ${soapNoteId} not found`);
  }
  if (!isSoapNoteEditable(existing.status)) {
    throw new Error(`SOAP note ${soapNoteId} is not editable in its current status`);
  }

  const display = resolveDisplay(input);
  const now = new Date().toISOString();

  const updated: SOAPNoteDetail = {
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
    clinical_note_id: input.clinical_note_id,
    clinical_note_number:
      input.clinical_note_id === existing.clinical_note_id
        ? existing.clinical_note_number
        : display.clinical_note_number,
    status,
    updated_at: now,
    subjective: input.subjective || null,
    objective: input.objective || null,
    assessment: input.assessment || null,
    plan: input.plan || null,
  };

  soapNotes = [...soapNotes.slice(0, index), updated, ...soapNotes.slice(index + 1)];
  return mockFetch(updated, 500);
}

export function soapNoteToFormInput(note: SOAPNoteDetail): SOAPNoteFormInput {
  return {
    patient_id: note.patient_id,
    visit_id: note.visit_id,
    doctor_id: note.doctor_id,
    clinical_note_id: note.clinical_note_id,
    subjective: note.subjective ?? "",
    objective: note.objective ?? "",
    assessment: note.assessment ?? "",
    plan: note.plan ?? "",
  };
}
