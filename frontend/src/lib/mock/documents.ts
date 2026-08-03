// Temporary frontend mock repository for Medical Documents Management
// (`app/(dashboard)/dashboard/documents/*`). No backend API is consumed
// anywhere in this module — every function below reads from and writes
// to an in-memory array, standing in for the backend "Personal Health
// Document Vault" module (`app.modules.documents`, aggregate
// `MedicalDocument`) — a genuinely distinct module from
// `app.modules.attachments`'s `VisitAttachment` (already reused by
// Visit/Clinical Notes/SOAP Notes/Lab Reports for their own lightweight
// "Attachments" sections). `MedicalDocument` is the real, general
// document vault: it actually uploads/stores file bytes via a
// `StoragePort`, has a real category taxonomy, real tags, and a real
// lifecycle status — none of which `VisitAttachment` has.
//
// Field names are grounded in the real domain entity
// (`app.modules.documents.domain.entities.MedicalDocument`):
// `organization_id, patient_id, uploaded_by_user_id, category, title,
// original_filename, stored_filename, mime_type, extension,
// file_size_bytes, storage_provider, storage_path, checksum_sha256,
// uploaded_at, visit_id, appointment_id, status, description, tags,
// metadata`. `DocumentCategory`/`DocumentStatus`/`StorageProvider` match
// `domain/enums.py` verbatim. `status` is a real, linear lifecycle
// (`Uploading → Active → Archived → Deleted`, no reverse transitions) —
// `isDocumentEditable()` mirrors that: once Archived or Deleted, a
// document is effectively read-only (the real `update_details` use case
// isn't itself status-gated in the backend, but editing an
// archived/deleted document doesn't make practical sense given the
// lifecycle is one-way, so this mock applies the same discipline every
// other status-driven module in this app already does).
//
// `stored_filename`/`storage_path`/`checksum_sha256`/`metadata` are
// deliberately not modeled — nothing in this module's UI displays raw
// storage internals, the same reasoning `lib/mock/visits.ts` already
// applies to fields no component reads.
//
// Real, direct relational fields: `patient_id` (required),
// `visit_id`/`appointment_id` (both optional). There is NO real FK to a
// clinical note, lab order/result, or prescription anywhere in this
// module (confirmed: grepped the whole real module, zero hits beyond an
// unrelated docstring example). "Related Clinical Note"/"Related Lab
// Report"/"Related Prescription" are therefore all derived the same way
// this app already derives "Related Diagnosis" elsewhere — via the
// document's own `visit_id`, matched against `getClinicalNoteByVisitId`/
// `getLabReportByVisitId`/`getPrescriptionByVisitId` (the latter two
// added alongside this module, see their own docstrings).
//
// `version_history` has zero backend basis — each real upload is a
// wholly independent row, there's no versioning concept anywhere in the
// real module. Generated deterministically per seeded document purely
// for the task's explicit "Version History (UI)" section — the "(UI)"
// qualifier there matches this being presentation-only, same spirit as
// "Drag & Drop uploader (UI)"/"Progress indicator (UI)" elsewhere in
// this module's own task description.
//
// `patient_name`/`patient_number`/`uploaded_by_name`/`visit_number`/
// `appointment_number` are denormalized display fields, same reasoning
// as every other mock repository in this app.

import type { PaginatedResponse } from "@/types";

const MIN_LATENCY_MS = 350;

function mockFetch<T>(value: T, latencyMs: number = MIN_LATENCY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), latencyMs));
}

function generateId(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

// --- Enums (verbatim from `app.modules.documents.domain.enums`) -------

export type DocumentCategory =
  | "prescription"
  | "lab_report"
  | "radiology"
  | "medical_image"
  | "clinical_note"
  | "referral_letter"
  | "discharge_summary"
  | "insurance"
  | "consent_form"
  | "vaccination"
  | "other";

export type DocumentStatus = "uploading" | "active" | "archived" | "deleted";

export type StorageProvider = "local" | "s3" | "azure_blob" | "google_cloud_storage";

export const DOCUMENT_CATEGORY_OPTIONS: { label: string; value: DocumentCategory }[] = [
  { label: "Prescription", value: "prescription" },
  { label: "Lab Report", value: "lab_report" },
  { label: "Radiology", value: "radiology" },
  { label: "Medical Image", value: "medical_image" },
  { label: "Clinical Note", value: "clinical_note" },
  { label: "Referral Letter", value: "referral_letter" },
  { label: "Discharge Summary", value: "discharge_summary" },
  { label: "Insurance", value: "insurance" },
  { label: "Consent Form", value: "consent_form" },
  { label: "Vaccination", value: "vaccination" },
  { label: "Other", value: "other" },
];

export const DOCUMENT_STATUS_OPTIONS: { label: string; value: DocumentStatus }[] = [
  { label: "Uploading", value: "uploading" },
  { label: "Active", value: "active" },
  { label: "Archived", value: "archived" },
  { label: "Deleted", value: "deleted" },
];

export function getDocumentCategoryLabel(category: DocumentCategory): string {
  return DOCUMENT_CATEGORY_OPTIONS.find((option) => option.value === category)?.label ?? category;
}

export function getDocumentStatusLabel(status: DocumentStatus): string {
  return DOCUMENT_STATUS_OPTIONS.find((option) => option.value === status)?.label ?? status;
}

export function isDocumentEditable(status: DocumentStatus): boolean {
  return status === "active" || status === "uploading";
}

// --- Core shapes ---------------------------------------------------------

export interface DocumentVersionEntry {
  version_id: string;
  version_number: number;
  uploaded_at: string;
  uploaded_by_name: string;
  file_size_bytes: number;
  note: string | null;
}

export interface MedicalDocument {
  document_id: string;
  document_number: string;
  organization_id: string;
  patient_id: string;
  patient_name: string;
  patient_number: string;
  uploaded_by_user_id: string;
  uploaded_by_name: string;
  category: DocumentCategory;
  title: string;
  original_filename: string;
  mime_type: string;
  extension: string;
  file_size_bytes: number;
  status: DocumentStatus;
  visit_id: string | null;
  visit_number: string | null;
  appointment_id: string | null;
  uploaded_at: string; // ISO 8601
}

export interface MedicalDocumentDetail extends MedicalDocument {
  description: string | null;
  tags: string[];
  storage_provider: StorageProvider;
  version_history: DocumentVersionEntry[];
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

function buildVersionHistory(
  uploadedAt: Date,
  uploadedByName: string,
  sizeBytes: number,
): DocumentVersionEntry[] {
  return [
    {
      version_id: generateId("ver"),
      version_number: 1,
      uploaded_at: uploadedAt.toISOString(),
      uploaded_by_name: uploadedByName,
      file_size_bytes: sizeBytes,
      note: "Initial upload.",
    },
  ];
}

interface DocumentSeed {
  patient_id: string;
  patient_name: string;
  patient_number: string;
  uploaded_by_name: string;
  visit_id: string | null;
  visit_number: string | null;
  category: DocumentCategory;
  title: string;
  original_filename: string;
  mime_type: string;
  extension: string;
  file_size_bytes: number;
  status: DocumentStatus;
  dayOffset: number;
  tags: string[];
  description: string | null;
}

const SEED: DocumentSeed[] = [
  {
    patient_id: "pat-0001",
    patient_name: "Michael Chen",
    patient_number: "PAT-100001",
    uploaded_by_name: "Dr. Amara Okafor",
    visit_id: "vis8-0001",
    visit_number: "VIS-80001",
    category: "lab_report",
    title: "Annual Physical Lab Results",
    original_filename: "annual_physical_labs.pdf",
    mime_type: "application/pdf",
    extension: "pdf",
    file_size_bytes: 245_000,
    status: "active",
    dayOffset: 0,
    tags: ["annual-checkup", "bloodwork"],
    description: "Complete blood panel from annual physical exam.",
  },
  {
    patient_id: "pat-0001",
    patient_name: "Michael Chen",
    patient_number: "PAT-100001",
    uploaded_by_name: "Front Desk",
    visit_id: null,
    visit_number: null,
    category: "insurance",
    title: "Insurance Card - Front and Back",
    original_filename: "insurance_card.jpg",
    mime_type: "image/jpeg",
    extension: "jpg",
    file_size_bytes: 1_240_000,
    status: "active",
    dayOffset: -30,
    tags: ["insurance"],
    description: "Scanned copy of current insurance card.",
  },
  {
    patient_id: "pat-0002",
    patient_name: "Sarah Johnson",
    patient_number: "PAT-100002",
    uploaded_by_name: "Dr. Amara Okafor",
    visit_id: "vis8-0002",
    visit_number: "VIS-80002",
    category: "prescription",
    title: "Amoxicillin Prescription",
    original_filename: "amoxicillin_rx.pdf",
    mime_type: "application/pdf",
    extension: "pdf",
    file_size_bytes: 98_000,
    status: "active",
    dayOffset: 0,
    tags: ["antibiotic"],
    description: null,
  },
  {
    patient_id: "pat-0004",
    patient_name: "David Kim",
    patient_number: "PAT-100004",
    uploaded_by_name: "Dr. Daniel Reyes",
    visit_id: "vis8-0003",
    visit_number: "VIS-80003",
    category: "lab_report",
    title: "Lipid Panel Results",
    original_filename: "lipid_panel.pdf",
    mime_type: "application/pdf",
    extension: "pdf",
    file_size_bytes: 187_000,
    status: "active",
    dayOffset: -1,
    tags: ["cholesterol", "bloodwork"],
    description: "Follow-up lipid panel.",
  },
  {
    patient_id: "pat-0003",
    patient_name: "Amara Nwosu",
    patient_number: "PAT-100003",
    uploaded_by_name: "Dr. Amara Okafor",
    visit_id: "vis8-0004",
    visit_number: "VIS-80004",
    category: "clinical_note",
    title: "Diabetes Follow-up Note",
    original_filename: "diabetes_followup.pdf",
    mime_type: "application/pdf",
    extension: "pdf",
    file_size_bytes: 156_000,
    status: "active",
    dayOffset: -2,
    tags: ["diabetes", "chronic-care"],
    description: null,
  },
  {
    patient_id: "pat-0003",
    patient_name: "Amara Nwosu",
    patient_number: "PAT-100003",
    uploaded_by_name: "Front Desk",
    visit_id: null,
    visit_number: null,
    category: "vaccination",
    title: "Flu Vaccination Record",
    original_filename: "flu_vaccine_2026.pdf",
    mime_type: "application/pdf",
    extension: "pdf",
    file_size_bytes: 64_000,
    status: "active",
    dayOffset: -45,
    tags: ["vaccination", "immunization"],
    description: "Annual influenza vaccination record.",
  },
  {
    patient_id: "pat-0006",
    patient_name: "James Williams",
    patient_number: "PAT-100006",
    uploaded_by_name: "Dr. Marcus Webb",
    visit_id: "vis8-0005",
    visit_number: "VIS-80005",
    category: "radiology",
    title: "Knee X-Ray",
    original_filename: "knee_xray.png",
    mime_type: "image/png",
    extension: "png",
    file_size_bytes: 3_450_000,
    status: "active",
    dayOffset: -3,
    tags: ["orthopedics", "imaging"],
    description: "Left knee, AP and lateral views.",
  },
  {
    patient_id: "pat-0011",
    patient_name: "Robert Lee",
    patient_number: "PAT-100011",
    uploaded_by_name: "Dr. Marcus Webb",
    visit_id: null,
    visit_number: null,
    category: "discharge_summary",
    title: "Post-Surgical Discharge Summary",
    original_filename: "discharge_summary.pdf",
    mime_type: "application/pdf",
    extension: "pdf",
    file_size_bytes: 210_000,
    status: "archived",
    dayOffset: -60,
    tags: ["surgery", "discharge"],
    description: "Discharge instructions following knee surgery.",
  },
  {
    patient_id: "pat-0013",
    patient_name: "Noah Thompson",
    patient_number: "PAT-100013",
    uploaded_by_name: "Dr. Amara Okafor",
    visit_id: null,
    visit_number: null,
    category: "referral_letter",
    title: "Endocrinology Referral",
    original_filename: "endo_referral.pdf",
    mime_type: "application/pdf",
    extension: "pdf",
    file_size_bytes: 72_000,
    status: "active",
    dayOffset: -4,
    tags: ["referral"],
    description: null,
  },
  {
    patient_id: "pat-0016",
    patient_name: "Sofia Torres",
    patient_number: "PAT-100016",
    uploaded_by_name: "Dr. Hannah Kim",
    visit_id: "vis8-0008",
    visit_number: "VIS-80008",
    category: "medical_image",
    title: "Skin Lesion Photo",
    original_filename: "skin_lesion.jpg",
    mime_type: "image/jpeg",
    extension: "jpg",
    file_size_bytes: 890_000,
    status: "active",
    dayOffset: -6,
    tags: ["dermatology", "imaging"],
    description: "Pre-biopsy reference photo.",
  },
  {
    patient_id: "pat-0014",
    patient_name: "Ava Rodriguez",
    patient_number: "PAT-100014",
    uploaded_by_name: "Front Desk",
    visit_id: null,
    visit_number: null,
    category: "consent_form",
    title: "Treatment Consent Form",
    original_filename: "consent_form_signed.pdf",
    mime_type: "application/pdf",
    extension: "pdf",
    file_size_bytes: 54_000,
    status: "active",
    dayOffset: -10,
    tags: ["consent"],
    description: "Signed consent for vaccination.",
  },
  {
    patient_id: "pat-0008",
    patient_name: "Ethan Brown",
    patient_number: "PAT-100008",
    uploaded_by_name: "Ethan Brown",
    visit_id: "vis8-0010",
    visit_number: "VIS-80010",
    category: "other",
    title: "Home BP Monitoring Log",
    original_filename: "bp_log.pdf",
    mime_type: "application/pdf",
    extension: "pdf",
    file_size_bytes: 41_000,
    status: "archived",
    dayOffset: -14,
    tags: ["hypertension", "self-reported"],
    description: "Two weeks of home blood pressure readings.",
  },
];

let documents: MedicalDocumentDetail[] = SEED.map((seed, index) => {
  const num = index + 1;
  const document_id = `doc-${String(num).padStart(4, "0")}`;
  const uploadedAt = atTime(dateOffset(seed.dayOffset), "10:00");

  return {
    document_id,
    document_number: `DOC-${90000 + num}`,
    organization_id: ORG_ID,
    patient_id: seed.patient_id,
    patient_name: seed.patient_name,
    patient_number: seed.patient_number,
    uploaded_by_user_id: generateId("user"),
    uploaded_by_name: seed.uploaded_by_name,
    category: seed.category,
    title: seed.title,
    original_filename: seed.original_filename,
    mime_type: seed.mime_type,
    extension: seed.extension,
    file_size_bytes: seed.file_size_bytes,
    status: seed.status,
    visit_id: seed.visit_id,
    visit_number: seed.visit_number,
    appointment_id: null,
    uploaded_at: uploadedAt.toISOString(),
    description: seed.description,
    tags: seed.tags,
    storage_provider: "local",
    version_history: buildVersionHistory(uploadedAt, seed.uploaded_by_name, seed.file_size_bytes),
  };
});

// --- Repository: reads -----------------------------------------------

export interface DocumentListParams {
  search?: string;
  status?: DocumentStatus | "all";
  category?: DocumentCategory | "all";
  sortBy?: "title" | "category" | "status" | "uploaded_at" | "patient_name" | "file_size_bytes";
  sortDirection?: "asc" | "desc";
  page?: number;
  pageSize?: number;
}

function matchesSearch(document: MedicalDocument, search: string): boolean {
  const needle = search.trim().toLowerCase();
  if (!needle) return true;
  return (
    document.document_number.toLowerCase().includes(needle) ||
    document.title.toLowerCase().includes(needle) ||
    document.original_filename.toLowerCase().includes(needle) ||
    document.patient_name.toLowerCase().includes(needle) ||
    document.uploaded_by_name.toLowerCase().includes(needle)
  );
}

function sortKey(
  document: MedicalDocument,
  sortBy: NonNullable<DocumentListParams["sortBy"]>,
): string | number {
  return document[sortBy] ?? "";
}

function stripDetail(document: MedicalDocumentDetail): MedicalDocument {
  return {
    document_id: document.document_id,
    document_number: document.document_number,
    organization_id: document.organization_id,
    patient_id: document.patient_id,
    patient_name: document.patient_name,
    patient_number: document.patient_number,
    uploaded_by_user_id: document.uploaded_by_user_id,
    uploaded_by_name: document.uploaded_by_name,
    category: document.category,
    title: document.title,
    original_filename: document.original_filename,
    mime_type: document.mime_type,
    extension: document.extension,
    file_size_bytes: document.file_size_bytes,
    status: document.status,
    visit_id: document.visit_id,
    visit_number: document.visit_number,
    appointment_id: document.appointment_id,
    uploaded_at: document.uploaded_at,
  };
}

// Excludes soft-deleted documents by default — matches how every other
// mock repository in this app treats a terminal/deleted state as hidden
// from normal list views unless explicitly filtered for.
export function listDocuments(
  params: DocumentListParams = {},
): Promise<PaginatedResponse<MedicalDocument>> {
  const {
    search = "",
    status = "all",
    category = "all",
    sortBy = "uploaded_at",
    sortDirection = "desc",
    page = 1,
    pageSize = 12,
  } = params;

  let filtered = documents.filter((document) => matchesSearch(document, search));
  filtered =
    status === "all"
      ? filtered.filter((document) => document.status !== "deleted")
      : filtered.filter((document) => document.status === status);
  if (category !== "all") {
    filtered = filtered.filter((document) => document.category === category);
  }

  const sorted = [...filtered].sort((a, b) => {
    const left = sortKey(a, sortBy);
    const right = sortKey(b, sortBy);
    const comparison =
      typeof left === "number" && typeof right === "number"
        ? left - right
        : String(left).localeCompare(String(right));
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

export function getDocument(documentId: string): Promise<MedicalDocumentDetail | null> {
  const found = documents.find((document) => document.document_id === documentId) ?? null;
  return mockFetch(found, 300);
}

// --- Repository: writes -------------------------------------------------
// `organization_id`/`uploaded_by_user_id`/`status`/`stored_filename`/
// `storage_path`/`checksum_sha256` are deliberately absent from this
// input shape — all server-controlled on the real `POST /documents`
// endpoint, never client-supplied. `visit_id`/`appointment_id` aren't
// part of this module's Upload form either (not requested by this
// task), so newly-created documents are always patient-level only —
// only the seeded seed data demonstrates the optional visit link, for
// the "Related Visit"/indirect-relationship sections' benefit.

// `tags` stays a plain comma-separated string here (same discipline as
// Prescriptions' `refills`) — it's typed into a single free-text
// `<input>`, so the DOM value is always a string regardless of the
// eventual array shape; splitting into `string[]` happens only at the
// write boundary below, via `parseTags()`.
export interface DocumentUploadInput {
  patient_id: string;
  category: DocumentCategory;
  title: string;
  original_filename: string;
  mime_type: string;
  extension: string;
  file_size_bytes: number;
  description: string;
  tags: string;
}

export interface DocumentUpdateInput {
  title: string;
  category: DocumentCategory;
  description: string;
  tags: string;
}

function parseTags(rawTags: string): string[] {
  return rawTags
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function resolvePatientDisplay(patientId: string): { name: string; number: string } {
  const existing = documents.find((document) => document.patient_id === patientId);
  return existing
    ? { name: existing.patient_name, number: existing.patient_number }
    : { name: "Unknown Patient", number: "—" };
}

export async function createDocument(input: DocumentUploadInput): Promise<MedicalDocumentDetail> {
  const id = generateId("doc");
  const nextNumber = 90000 + documents.length + 1;
  const patient = resolvePatientDisplay(input.patient_id);
  const now = new Date();

  const created: MedicalDocumentDetail = {
    document_id: id,
    document_number: `DOC-${nextNumber}`,
    organization_id: ORG_ID,
    patient_id: input.patient_id,
    patient_name: patient.name,
    patient_number: patient.number,
    uploaded_by_user_id: generateId("user"),
    uploaded_by_name: "You",
    category: input.category,
    title: input.title,
    original_filename: input.original_filename,
    mime_type: input.mime_type,
    extension: input.extension,
    file_size_bytes: input.file_size_bytes,
    status: "active",
    visit_id: null,
    visit_number: null,
    appointment_id: null,
    uploaded_at: now.toISOString(),
    description: input.description || null,
    tags: parseTags(input.tags),
    storage_provider: "local",
    version_history: buildVersionHistory(now, "You", input.file_size_bytes),
  };

  documents = [created, ...documents];
  return mockFetch(created, 600);
}

export async function updateDocument(
  documentId: string,
  input: DocumentUpdateInput,
): Promise<MedicalDocumentDetail> {
  const index = documents.findIndex((document) => document.document_id === documentId);
  const existing = documents[index];
  if (!existing) {
    throw new Error(`Document ${documentId} not found`);
  }
  if (!isDocumentEditable(existing.status)) {
    throw new Error(`Document ${documentId} is not editable in its current status`);
  }

  const updated: MedicalDocumentDetail = {
    ...existing,
    title: input.title,
    category: input.category,
    description: input.description || null,
    tags: parseTags(input.tags),
  };

  documents = [...documents.slice(0, index), updated, ...documents.slice(index + 1)];
  return mockFetch(updated, 500);
}

export function documentToFormInput(document: MedicalDocumentDetail): DocumentUpdateInput {
  return {
    title: document.title,
    category: document.category,
    description: document.description ?? "",
    tags: document.tags.join(", "),
  };
}
