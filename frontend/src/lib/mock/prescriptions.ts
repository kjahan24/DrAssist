// Temporary frontend mock repository for Prescription Management
// (`app/(dashboard)/dashboard/prescriptions/*`). No backend API is
// consumed anywhere in this module — every function below reads from
// and writes to an in-memory array, standing in for the backend
// Prescriptions module (`app.modules.prescriptions`) until its REST
// endpoints grow beyond their current scope (today: `POST /`,
// `GET /clinical-note/{id}`, `GET /{id}`, `GET /` search,
// `GET /patient/{id}`, `PUT /{id}`, `POST /{id}/items`,
// `PATCH /{id}/finalize` — no cancel/void/delete endpoint exists).
//
// Field names are grounded in the real domain entities
// (`app.modules.prescriptions.domain.entities`), a one-to-one child of
// `ClinicalNote`: `Prescription` — `organization_id, clinical_note_id,
// patient_id, visit_id, doctor_id, prescription_number,
// prescription_date, status (PrescriptionStatus: draft|final), notes`.
// `PrescriptionItem` (a separate top-level aggregate, referenced by
// `prescription_id`) — `medication_name, generic_name, strength,
// dosage, dosage_unit, frequency, route (AdministrationRoute, imported
// from `lib/mock/medications.ts`), duration, duration_unit, quantity,
// instructions`. Unlike `ClinicalNote`/`LabOrder`, `Prescription`'s real
// `status` is already the exact two-value Draft/Final this module's
// forms ask for — no unification/derivation needed here, unlike
// `lib/mock/lab-reports.ts`'s 5-state `LabReportStatus`.
//
// One deliberate frontend-only addition: `PrescriptionItem.refills` —
// confirmed absent from the real backend entirely (searched
// `domain/entities.py`, `domain/enums.py`, `api/schemas.py`,
// `infrastructure/models.py`, and the whole `backend/` tree for
// "refill" case-insensitively; the word appears only in doc-comments
// naming a future out-of-scope "Refill Requests" module, never as a
// field). Added purely because this module's Create form and detail
// page's Medication List explicitly ask for a "Refills" value per
// medication.
//
// `Prescription` here is a fresh, standalone, fully-identified type —
// deliberately NOT the lighter `VisitPrescription`/`PrescriptionItem`
// pair already embedded in `lib/mock/visits.ts` (which lack top-level
// identity FKs since they're only ever nested inside a `VisitDetail`/
// `SOAPNoteDetail`). This module needs the full aggregate identity
// (`prescription_id`, `patient_name`, `doctor_name`, `visit_number`,
// `clinical_note_number` for display, etc.) the same way every other
// top-level module (Appointments, Visits, Clinical Notes, SOAP Notes,
// Lab Reports) already does. `diagnoses` reuses `VisitDiagnosis` from
// `lib/mock/visits.ts` for "Related Diagnosis" — `Prescription` only
// shares `visit_id` with diagnoses in the real backend, no direct FK
// (confirmed: zero diagnosis references anywhere in the real
// prescriptions module), so this mirrors the exact same
// visit_id-only relationship SOAP Notes and Lab Reports already model.
//
// `patient_name`/`patient_number`/`doctor_name`/`visit_number`/
// `clinical_note_number` are denormalized display fields, same
// reasoning as every other mock repository in this app.

import type { PaginatedResponse } from "@/types";
import { type AdministrationRoute } from "@/lib/mock/medications";
import type { VisitDiagnosis } from "@/lib/mock/visits";

const MIN_LATENCY_MS = 350;

function mockFetch<T>(value: T, latencyMs: number = MIN_LATENCY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), latencyMs));
}

function generateId(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

// --- Status ---------------------------------------------------------

export type PrescriptionStatus = "draft" | "final";

export const PRESCRIPTION_STATUS_OPTIONS: { label: string; value: PrescriptionStatus }[] = [
  { label: "Draft", value: "draft" },
  { label: "Final", value: "final" },
];

export function getPrescriptionStatusLabel(status: PrescriptionStatus): string {
  return PRESCRIPTION_STATUS_OPTIONS.find((option) => option.value === status)?.label ?? status;
}

// Mirrors the real, strict rule: both `update_prescription` and
// `add_prescription_item` are gated Draft-only
// (`Prescription.ensure_editable()`).
export function isPrescriptionEditable(status: PrescriptionStatus): boolean {
  return status === "draft";
}

// --- Core shapes ---------------------------------------------------------

export interface PrescriptionItem {
  prescription_item_id: string;
  prescription_id: string;
  medication_name: string;
  generic_name: string | null;
  strength: string;
  dosage: string;
  dosage_unit: string;
  frequency: string;
  route: AdministrationRoute;
  duration: string;
  duration_unit: string;
  quantity: string;
  instructions: string | null;
  refills: number;
}

export interface Prescription {
  prescription_id: string;
  organization_id: string;
  clinical_note_id: string;
  clinical_note_number: string;
  patient_id: string;
  patient_name: string;
  patient_number: string;
  doctor_id: string;
  doctor_name: string;
  visit_id: string;
  visit_number: string;
  prescription_number: string;
  prescription_date: string; // ISO 8601 date
  status: PrescriptionStatus;
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
}

export interface PrescriptionDetail extends Prescription {
  notes: string | null;
  items: PrescriptionItem[];
  diagnoses: VisitDiagnosis[];
  created_by_name: string;
  updated_by_name: string;
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

interface PrescriptionSeed {
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
  status: PrescriptionStatus;
  items: Omit<PrescriptionItem, "prescription_item_id" | "prescription_id">[];
  diagnoses: Omit<VisitDiagnosis, "diagnosis_id">[];
}

const SEED: PrescriptionSeed[] = [
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
    items: [
      {
        medication_name: "Lisinopril",
        generic_name: "Lisinopril",
        strength: "10 mg",
        dosage: "1 tablet",
        dosage_unit: "tablet",
        frequency: "Once daily",
        route: "oral",
        duration: "90",
        duration_unit: "days",
        quantity: "90",
        instructions: "Take in the morning with water.",
        refills: 3,
      },
    ],
    diagnoses: [
      {
        sequence_number: 1,
        diagnosis_name: "Essential hypertension",
        diagnosis_type: "primary",
        icd10_code: "I10",
        diagnosis_status: "confirmed",
        diagnosed_at: new Date().toISOString(),
        clinical_notes: "Blood pressure well controlled on current regimen.",
      },
    ],
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
    items: [
      {
        medication_name: "Amoxicillin",
        generic_name: "Amoxicillin",
        strength: "500 mg",
        dosage: "1 capsule",
        dosage_unit: "capsule",
        frequency: "Three times daily",
        route: "oral",
        duration: "10",
        duration_unit: "days",
        quantity: "30",
        instructions: "Complete full course even if feeling better.",
        refills: 0,
      },
    ],
    diagnoses: [],
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
    items: [
      {
        medication_name: "Atorvastatin",
        generic_name: "Atorvastatin calcium",
        strength: "20 mg",
        dosage: "1 tablet",
        dosage_unit: "tablet",
        frequency: "Once daily at bedtime",
        route: "oral",
        duration: "90",
        duration_unit: "days",
        quantity: "90",
        instructions: "Take at bedtime; avoid grapefruit juice.",
        refills: 3,
      },
    ],
    diagnoses: [
      {
        sequence_number: 1,
        diagnosis_name: "Hyperlipidemia",
        diagnosis_type: "primary",
        icd10_code: "E78.5",
        diagnosis_status: "confirmed",
        diagnosed_at: new Date().toISOString(),
        clinical_notes: "Elevated LDL, dietary counseling also provided.",
      },
    ],
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
    items: [
      {
        medication_name: "Metformin",
        generic_name: "Metformin HCl",
        strength: "500 mg",
        dosage: "1 tablet",
        dosage_unit: "tablet",
        frequency: "Twice daily",
        route: "oral",
        duration: "90",
        duration_unit: "days",
        quantity: "180",
        instructions: "Take with meals to reduce GI upset.",
        refills: 3,
      },
      {
        medication_name: "Atorvastatin",
        generic_name: "Atorvastatin calcium",
        strength: "10 mg",
        dosage: "1 tablet",
        dosage_unit: "tablet",
        frequency: "Once daily at bedtime",
        route: "oral",
        duration: "90",
        duration_unit: "days",
        quantity: "90",
        instructions: null,
        refills: 3,
      },
    ],
    diagnoses: [
      {
        sequence_number: 1,
        diagnosis_name: "Type 2 diabetes mellitus",
        diagnosis_type: "primary",
        icd10_code: "E11.9",
        diagnosis_status: "confirmed",
        diagnosed_at: new Date().toISOString(),
        clinical_notes: "HbA1c 6.9%, reasonably controlled.",
      },
    ],
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
    items: [],
    diagnoses: [],
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
    items: [],
    diagnoses: [],
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
    items: [
      {
        medication_name: "Levothyroxine",
        generic_name: "Levothyroxine sodium",
        strength: "50 mcg",
        dosage: "1 tablet",
        dosage_unit: "tablet",
        frequency: "Once daily",
        route: "oral",
        duration: "90",
        duration_unit: "days",
        quantity: "90",
        instructions: "Take on an empty stomach, 30 minutes before breakfast.",
        refills: 3,
      },
    ],
    diagnoses: [],
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
    items: [],
    diagnoses: [],
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
    items: [],
    diagnoses: [],
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
    items: [],
    diagnoses: [],
  },
];

let prescriptions: PrescriptionDetail[] = SEED.map((seed, index) => {
  const num = index + 1;
  const prescription_id = `presc-${String(num).padStart(4, "0")}`;
  const prescriptionDate = dateOffset(seed.dayOffset);
  const issuedAt = atTime(prescriptionDate, seed.nominalTime);
  const createdAt = new Date(issuedAt.getTime() + 15 * 60_000);
  const updatedAt =
    seed.status === "final" ? new Date(createdAt.getTime() + 20 * 60_000) : createdAt;

  const items: PrescriptionItem[] = seed.items.map((item) => ({
    ...item,
    prescription_item_id: generateId("rxitem"),
    prescription_id,
  }));

  const diagnoses: VisitDiagnosis[] = seed.diagnoses.map((diagnosis) => ({
    ...diagnosis,
    diagnosis_id: generateId("dx"),
  }));

  return {
    prescription_id,
    organization_id: ORG_ID,
    clinical_note_id: seed.clinical_note_id,
    clinical_note_number: seed.clinical_note_number,
    patient_id: seed.patient_id,
    patient_name: seed.patient_name,
    patient_number: seed.patient_number,
    doctor_id: seed.doctor_id,
    doctor_name: seed.doctor_name,
    visit_id: seed.visit_id,
    visit_number: seed.visit_number,
    prescription_number: `RX-${80000 + num}`,
    prescription_date: prescriptionDate,
    status: seed.status,
    created_at: createdAt.toISOString(),
    updated_at: updatedAt.toISOString(),
    notes:
      items.length > 0
        ? "Reviewed medication list with patient; no known allergies to prescribed agents."
        : null,
    items,
    diagnoses,
    created_by_name: seed.doctor_name,
    updated_by_name: seed.doctor_name,
  };
});

// --- Repository: reads -----------------------------------------------

export interface PrescriptionListParams {
  search?: string;
  status?: PrescriptionStatus | "all";
  sortBy?: "prescription_number" | "patient_name" | "doctor_name" | "prescription_date" | "status";
  sortDirection?: "asc" | "desc";
  page?: number;
  pageSize?: number;
}

function matchesSearch(prescription: Prescription, search: string): boolean {
  const needle = search.trim().toLowerCase();
  if (!needle) return true;
  return (
    prescription.prescription_number.toLowerCase().includes(needle) ||
    prescription.patient_name.toLowerCase().includes(needle) ||
    prescription.doctor_name.toLowerCase().includes(needle) ||
    prescription.visit_number.toLowerCase().includes(needle)
  );
}

function sortKey(
  prescription: Prescription,
  sortBy: NonNullable<PrescriptionListParams["sortBy"]>,
): string {
  return String(prescription[sortBy] ?? "");
}

function stripDetail(prescription: PrescriptionDetail): Prescription {
  return {
    prescription_id: prescription.prescription_id,
    organization_id: prescription.organization_id,
    clinical_note_id: prescription.clinical_note_id,
    clinical_note_number: prescription.clinical_note_number,
    patient_id: prescription.patient_id,
    patient_name: prescription.patient_name,
    patient_number: prescription.patient_number,
    doctor_id: prescription.doctor_id,
    doctor_name: prescription.doctor_name,
    visit_id: prescription.visit_id,
    visit_number: prescription.visit_number,
    prescription_number: prescription.prescription_number,
    prescription_date: prescription.prescription_date,
    status: prescription.status,
    created_at: prescription.created_at,
    updated_at: prescription.updated_at,
  };
}

export function listPrescriptions(
  params: PrescriptionListParams = {},
): Promise<PaginatedResponse<Prescription>> {
  const {
    search = "",
    status = "all",
    sortBy = "prescription_date",
    sortDirection = "desc",
    page = 1,
    pageSize = 10,
  } = params;

  let filtered = prescriptions.filter((prescription) => matchesSearch(prescription, search));
  if (status !== "all") {
    filtered = filtered.filter((prescription) => prescription.status === status);
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

export function getPrescription(prescriptionId: string): Promise<PrescriptionDetail | null> {
  const found =
    prescriptions.find((prescription) => prescription.prescription_id === prescriptionId) ?? null;
  return mockFetch(found, 300);
}

// Added for the Medical Documents module (`lib/mock/documents.ts`): a
// document's "Related Prescription" section has no real backend FK to
// derive from (`MedicalDocument` only has `visit_id`/`appointment_id`,
// no `prescription_id`) — same shared-`visit_id` indirection already
// used elsewhere in this app. Mirrors `getLabReportByVisitId()` exactly.
export function getPrescriptionByVisitId(visitId: string): Promise<PrescriptionDetail | null> {
  const found = prescriptions.find((prescription) => prescription.visit_id === visitId) ?? null;
  return mockFetch(found, 200);
}

// --- Repository: writes -------------------------------------------------
// `patient_id`/`doctor_id`/`visit_id` are deliberately absent from this
// input shape — mirroring the real `Prescription`, they're derived from
// the selected clinical note (itself derived from the selected visit),
// not independently supplied.

// Mirrors `PrescriptionItem` but with every field a plain (non-nullable)
// string, including `refills` — form fields need a controlled string
// value: `generic_name`/`instructions` are nullable on the repository
// type (converted at the boundary, same as every other module's
// `*FormInput` type already does), and `refills` stays a string here
// specifically to sidestep a well-known React Hook Form + native
// `<input type="number">` footgun (the DOM's `value`/`onChange` are
// always strings regardless of the input's `type`, so a field typed
// `number` silently receives a string at runtime the moment a user
// types — every numeric-looking field in this app's forms has stayed a
// string for exactly this reason, e.g. quantity/duration above).
// Converted to a real `number` only in `toPrescriptionItems()`.
export interface PrescriptionItemFormInput {
  prescription_item_id: string;
  medication_name: string;
  generic_name: string;
  strength: string;
  dosage: string;
  dosage_unit: string;
  frequency: string;
  route: AdministrationRoute;
  duration: string;
  duration_unit: string;
  quantity: string;
  instructions: string;
  refills: string;
}

export interface PrescriptionFormInput {
  patient_id: string;
  visit_id: string;
  doctor_id: string;
  clinical_note_id: string;
  prescription_date: string;
  notes: string;
  items: PrescriptionItemFormInput[];
}

function toPrescriptionItems(
  items: PrescriptionItemFormInput[],
  prescriptionId: string,
): PrescriptionItem[] {
  return items.map((item) => ({
    prescription_item_id: item.prescription_item_id,
    prescription_id: prescriptionId,
    medication_name: item.medication_name,
    generic_name: item.generic_name || null,
    strength: item.strength,
    dosage: item.dosage,
    dosage_unit: item.dosage_unit,
    frequency: item.frequency,
    route: item.route,
    duration: item.duration,
    duration_unit: item.duration_unit,
    quantity: item.quantity,
    instructions: item.instructions || null,
    refills: Number(item.refills) || 0,
  }));
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
  const existing = prescriptions.find(
    (prescription) =>
      prescription.patient_id === input.patient_id ||
      prescription.doctor_id === input.doctor_id ||
      prescription.visit_id === input.visit_id ||
      prescription.clinical_note_id === input.clinical_note_id,
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

export async function createPrescription(
  input: PrescriptionFormInput,
  status: PrescriptionStatus,
): Promise<PrescriptionDetail> {
  const id = generateId("presc");
  const nextNumber = 80000 + prescriptions.length + 1;
  const display = resolveDisplay(input);
  const now = new Date().toISOString();

  const created: PrescriptionDetail = {
    prescription_id: id,
    organization_id: ORG_ID,
    clinical_note_id: input.clinical_note_id,
    clinical_note_number: display.clinical_note_number,
    patient_id: input.patient_id,
    patient_name: display.patient_name,
    patient_number: display.patient_number,
    doctor_id: input.doctor_id,
    doctor_name: display.doctor_name,
    visit_id: input.visit_id,
    visit_number: display.visit_number,
    prescription_number: `RX-${nextNumber}`,
    prescription_date: input.prescription_date,
    status,
    created_at: now,
    updated_at: now,
    notes: input.notes || null,
    items: toPrescriptionItems(input.items, id),
    diagnoses: [],
    created_by_name: display.doctor_name,
    updated_by_name: display.doctor_name,
  };

  prescriptions = [created, ...prescriptions];
  return mockFetch(created, 500);
}

export async function updatePrescription(
  prescriptionId: string,
  input: PrescriptionFormInput,
  status: PrescriptionStatus,
): Promise<PrescriptionDetail> {
  const index = prescriptions.findIndex(
    (prescription) => prescription.prescription_id === prescriptionId,
  );
  const existing = prescriptions[index];
  if (!existing) {
    throw new Error(`Prescription ${prescriptionId} not found`);
  }
  if (!isPrescriptionEditable(existing.status)) {
    throw new Error(`Prescription ${prescriptionId} is not editable in its current status`);
  }

  const display = resolveDisplay(input);
  const now = new Date().toISOString();

  const updated: PrescriptionDetail = {
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
    prescription_date: input.prescription_date,
    status,
    updated_at: now,
    notes: input.notes || null,
    items: toPrescriptionItems(input.items, prescriptionId),
  };

  prescriptions = [...prescriptions.slice(0, index), updated, ...prescriptions.slice(index + 1)];
  return mockFetch(updated, 500);
}

export function prescriptionToFormInput(prescription: PrescriptionDetail): PrescriptionFormInput {
  return {
    patient_id: prescription.patient_id,
    visit_id: prescription.visit_id,
    doctor_id: prescription.doctor_id,
    clinical_note_id: prescription.clinical_note_id,
    prescription_date: prescription.prescription_date,
    notes: prescription.notes ?? "",
    items: prescription.items.map((item) => ({
      prescription_item_id: item.prescription_item_id,
      medication_name: item.medication_name,
      generic_name: item.generic_name ?? "",
      strength: item.strength,
      dosage: item.dosage,
      dosage_unit: item.dosage_unit,
      frequency: item.frequency,
      route: item.route,
      duration: item.duration,
      duration_unit: item.duration_unit,
      quantity: item.quantity,
      instructions: item.instructions ?? "",
      refills: String(item.refills),
    })),
  };
}
