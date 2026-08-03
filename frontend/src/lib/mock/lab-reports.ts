// Temporary frontend mock repository for Lab Reports Management
// (`app/(dashboard)/dashboard/lab-reports/*`). No backend API is
// consumed anywhere in this module — every function below reads from
// and writes to an in-memory array.
//
// IMPORTANT — there is no single "Lab Report" backend module. The real
// backend has two separate, chained Clean Architecture modules:
// `app.modules.lab_orders` (`LabOrder` → `LabOrderItem`, one-to-many —
// "what to test", one order per clinical note) and
// `app.modules.lab_results` (`LabResult` → `LabResultItem`, strictly
// one-to-one with its parent `LabOrder` — "what was found"). This
// module's pages/columns/sections ask for both order-side facts
// ("Ordered By", "Collected Date") and result-side facts ("Test
// Results", "Reference Ranges", "Interpretation") as ONE resource, so
// this mock unifies both real chains into a single `LabReport` type —
// the same collapsing strategy already used for Prescriptions
// (`VisitPrescription`) and SOAP Notes (7 real fields → 4 quadrants).
// Every field below is still grounded in one of the two real entities;
// see the per-field comments for which.
//
// Real `LabOrder` fields (`app.modules.lab_orders.domain.entities`):
// `organization_id, clinical_note_id, patient_id, visit_id, doctor_id,
// order_number, ordered_at, priority, status (LabOrderStatus:
// draft|ordered|collected|cancelled), clinical_information, notes`.
// Real `LabOrderItem`: `lab_order_id, test_code, test_name,
// specimen_type, status, specimen_site, instructions`.
// Real `LabResult` (`app.modules.lab_results.domain.entities`):
// `organization_id, lab_order_id, patient_id, visit_id, doctor_id,
// result_number, reported_at, status (LabResultStatus: draft|final),
// laboratory_name, comments`. Real `LabResultItem`: `lab_result_id,
// lab_order_item_id, test_code, test_name, result_value, abnormal_flag
// (AbnormalFlag: normal|low|high|critical|abnormal), result_unit,
// reference_range (a single free-text field, e.g. "70-100 mg/dL" — NOT
// a structured low/high value object; confirmed nothing else exists in
// the real backend), interpretation (per-test, not report-level).
//
// Three deliberate frontend-only additions, each called out because
// nothing real backs them:
//   - `LabReportCategory` — no category/panel enum exists anywhere in
//     either real module (`test_code`/`test_name` are uncontrolled free
//     text). Invented purely because this module's List "Category"
//     column and Create form "Report category" field explicitly ask
//     for one.
//   - `collected_at` — the real `LabOrder` only has a `status`
//     transition to COLLECTED, no dedicated timestamp field. Added
//     purely for the task's explicit "Collected Date" list column.
//   - `status` (`LabReportStatus`, the unified 5-value status this UI
//     actually filters/badges on) — derived from combining the real
//     `LabOrderStatus` and `LabResultStatus`: `cancelled` (order
//     cancelled) → `final` (result finalized) → `collected` (order
//     collected, no final result yet) → `ordered` → `draft`. The
//     underlying real statuses are still kept on `LabReportDetail`
//     (`order_status`/`result_status`) for fidelity.
//   - `LabTestItem` merges `LabOrderItem` (test_code/test_name/
//     specimen_type) with `LabResultItem` (result_value/result_unit/
//     reference_range/abnormal_flag/interpretation) into one row, since
//     this module's Create form asks for one combined "Test list" +
//     "Result editor" + "Reference range editor" per test, not two
//     separately-managed lists.
//
// `patient_name`/`patient_number`/`doctor_name`/`visit_number`/
// `clinical_note_number` are denormalized display fields, same
// reasoning as every other mock repository in this app. `attachments`
// reuses `VisitDocument` from `lib/mock/visits.ts` — neither real lab
// module has its own attachment entity; the real `VisitAttachment` is
// keyed strictly by `visit_id`, which both `LabOrder` and `LabResult`
// already carry directly, so a lab report's attachments are really its
// parent visit's attachments (identical reasoning to Clinical Notes'
// own "Attachments Summary").
//
// Editability mirrors the real, strict rule: both `update_lab_order`
// and `update_lab_result` are gated Draft-only
// (`LabOrder.ensure_editable()` / equivalent on `LabResult`) — so
// `isLabReportEditable()` only allows the fully-draft state, exactly
// like `lib/mock/clinical-notes.ts` and `lib/mock/soap-notes.ts`
// already do for their own single-status entities.

import type { PaginatedResponse } from "@/types";
import type { VisitDocument } from "@/lib/mock/visits";

const MIN_LATENCY_MS = 350;

function mockFetch<T>(value: T, latencyMs: number = MIN_LATENCY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), latencyMs));
}

function generateId(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

// --- Enums --------------------------------------------------------------

export type LabPriority = "routine" | "urgent" | "stat";
export type LabOrderStatus = "draft" | "ordered" | "collected" | "cancelled";
export type LabResultStatus = "draft" | "final";
export type AbnormalFlag = "normal" | "low" | "high" | "critical" | "abnormal";

// Unified list/badge/filter status — see this file's own docstring.
export type LabReportStatus = "draft" | "ordered" | "collected" | "final" | "cancelled";

// Frontend-only — see this file's own docstring.
export type LabReportCategory =
  | "hematology"
  | "chemistry"
  | "microbiology"
  | "immunology"
  | "urinalysis"
  | "pathology"
  | "radiology"
  | "other";

export const LAB_REPORT_CATEGORY_OPTIONS: { label: string; value: LabReportCategory }[] = [
  { label: "Hematology", value: "hematology" },
  { label: "Chemistry", value: "chemistry" },
  { label: "Microbiology", value: "microbiology" },
  { label: "Immunology", value: "immunology" },
  { label: "Urinalysis", value: "urinalysis" },
  { label: "Pathology", value: "pathology" },
  { label: "Radiology", value: "radiology" },
  { label: "Other", value: "other" },
];

export const LAB_PRIORITY_OPTIONS: { label: string; value: LabPriority }[] = [
  { label: "Routine", value: "routine" },
  { label: "Urgent", value: "urgent" },
  { label: "STAT", value: "stat" },
];

export const ABNORMAL_FLAG_OPTIONS: { label: string; value: AbnormalFlag }[] = [
  { label: "Normal", value: "normal" },
  { label: "Low", value: "low" },
  { label: "High", value: "high" },
  { label: "Critical", value: "critical" },
  { label: "Abnormal", value: "abnormal" },
];

export const LAB_REPORT_STATUS_OPTIONS: { label: string; value: LabReportStatus }[] = [
  { label: "Draft", value: "draft" },
  { label: "Ordered", value: "ordered" },
  { label: "Collected", value: "collected" },
  { label: "Final", value: "final" },
  { label: "Cancelled", value: "cancelled" },
];

export function getLabReportStatusLabel(status: LabReportStatus): string {
  return LAB_REPORT_STATUS_OPTIONS.find((option) => option.value === status)?.label ?? status;
}

export function getLabReportCategoryLabel(category: LabReportCategory): string {
  return LAB_REPORT_CATEGORY_OPTIONS.find((option) => option.value === category)?.label ?? category;
}

export function getAbnormalFlagLabel(flag: AbnormalFlag): string {
  return ABNORMAL_FLAG_OPTIONS.find((option) => option.value === flag)?.label ?? flag;
}

export function isLabReportEditable(status: LabReportStatus): boolean {
  return status === "draft";
}

// --- Core shapes ---------------------------------------------------------

export interface LabTestItem {
  item_id: string;
  test_code: string;
  test_name: string;
  specimen_type: string;
  result_value: string;
  result_unit: string;
  reference_range: string;
  abnormal_flag: AbnormalFlag;
  interpretation: string | null;
}

export interface LabReport {
  lab_report_id: string;
  organization_id: string;
  report_number: string;
  patient_id: string;
  patient_name: string;
  patient_number: string;
  doctor_id: string;
  doctor_name: string;
  visit_id: string;
  visit_number: string;
  clinical_note_id: string;
  clinical_note_number: string;
  category: LabReportCategory;
  priority: LabPriority;
  status: LabReportStatus;
  // A pre-computed summary of `items` (e.g. "Glucose +3 more") — not the
  // full item array, which stays detail-only — so the List page's "Test
  // Name" column doesn't require every list row to carry full result
  // data. See `getTestSummary()`.
  test_summary: string;
  ordered_at: string; // ISO 8601
  collected_at: string | null; // ISO 8601
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
}

export interface LabReportDetail extends LabReport {
  order_status: LabOrderStatus;
  result_status: LabResultStatus | null;
  clinical_information: string | null;
  interpretation: string | null;
  laboratory_name: string | null;
  reported_at: string | null;
  notes: string | null;
  items: LabTestItem[];
  attachments: VisitDocument[];
  created_by_name: string;
  updated_by_name: string;
}

export function getTestSummary(items: LabTestItem[]): string {
  if (items.length === 0) return "No tests";
  const [first, ...rest] = items;
  if (!first) return "No tests";
  return rest.length > 0 ? `${first.test_name} +${rest.length} more` : first.test_name;
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

interface LabReportSeed {
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
  category: LabReportCategory;
  priority: LabPriority;
  status: LabReportStatus;
  items: Omit<LabTestItem, "item_id">[];
}

const SEED: LabReportSeed[] = [
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
    category: "chemistry",
    priority: "routine",
    status: "final",
    items: [
      {
        test_code: "GLU",
        test_name: "Glucose",
        specimen_type: "Blood",
        result_value: "96",
        result_unit: "mg/dL",
        reference_range: "70-99 mg/dL",
        abnormal_flag: "normal",
        interpretation: null,
      },
      {
        test_code: "NA",
        test_name: "Sodium",
        specimen_type: "Blood",
        result_value: "140",
        result_unit: "mmol/L",
        reference_range: "135-145 mmol/L",
        abnormal_flag: "normal",
        interpretation: null,
      },
      {
        test_code: "K",
        test_name: "Potassium",
        specimen_type: "Blood",
        result_value: "4.2",
        result_unit: "mmol/L",
        reference_range: "3.5-5.0 mmol/L",
        abnormal_flag: "normal",
        interpretation: null,
      },
      {
        test_code: "CREAT",
        test_name: "Creatinine",
        specimen_type: "Blood",
        result_value: "1.0",
        result_unit: "mg/dL",
        reference_range: "0.7-1.3 mg/dL",
        abnormal_flag: "normal",
        interpretation: null,
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
    category: "hematology",
    priority: "routine",
    status: "final",
    items: [
      {
        test_code: "WBC",
        test_name: "White Blood Cell Count",
        specimen_type: "Blood",
        result_value: "6.8",
        result_unit: "x10^9/L",
        reference_range: "4.5-11.0 x10^9/L",
        abnormal_flag: "normal",
        interpretation: null,
      },
      {
        test_code: "RBC",
        test_name: "Red Blood Cell Count",
        specimen_type: "Blood",
        result_value: "4.7",
        result_unit: "x10^12/L",
        reference_range: "4.2-5.4 x10^12/L",
        abnormal_flag: "normal",
        interpretation: null,
      },
      {
        test_code: "HGB",
        test_name: "Hemoglobin",
        specimen_type: "Blood",
        result_value: "13.5",
        result_unit: "g/dL",
        reference_range: "12.0-15.5 g/dL",
        abnormal_flag: "normal",
        interpretation: null,
      },
      {
        test_code: "PLT",
        test_name: "Platelet Count",
        specimen_type: "Blood",
        result_value: "250",
        result_unit: "x10^9/L",
        reference_range: "150-450 x10^9/L",
        abnormal_flag: "normal",
        interpretation: null,
      },
    ],
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
    category: "chemistry",
    priority: "urgent",
    status: "final",
    items: [
      {
        test_code: "TC",
        test_name: "Total Cholesterol",
        specimen_type: "Blood",
        result_value: "215",
        result_unit: "mg/dL",
        reference_range: "<200 mg/dL",
        abnormal_flag: "high",
        interpretation: "Mildly elevated; recommend dietary counseling.",
      },
      {
        test_code: "LDL",
        test_name: "LDL Cholesterol",
        specimen_type: "Blood",
        result_value: "142",
        result_unit: "mg/dL",
        reference_range: "<100 mg/dL",
        abnormal_flag: "high",
        interpretation: "Elevated cardiovascular risk factor.",
      },
      {
        test_code: "HDL",
        test_name: "HDL Cholesterol",
        specimen_type: "Blood",
        result_value: "48",
        result_unit: "mg/dL",
        reference_range: ">40 mg/dL",
        abnormal_flag: "normal",
        interpretation: null,
      },
      {
        test_code: "TRIG",
        test_name: "Triglycerides",
        specimen_type: "Blood",
        result_value: "130",
        result_unit: "mg/dL",
        reference_range: "<150 mg/dL",
        abnormal_flag: "normal",
        interpretation: null,
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
    category: "chemistry",
    priority: "routine",
    status: "final",
    items: [
      {
        test_code: "HBA1C",
        test_name: "Hemoglobin A1c",
        specimen_type: "Blood",
        result_value: "6.9",
        result_unit: "%",
        reference_range: "<5.7 %",
        abnormal_flag: "high",
        interpretation: "Consistent with diagnosed type 2 diabetes, reasonably controlled.",
      },
      {
        test_code: "GLU",
        test_name: "Glucose (Fasting)",
        specimen_type: "Blood",
        result_value: "118",
        result_unit: "mg/dL",
        reference_range: "70-99 mg/dL",
        abnormal_flag: "high",
        interpretation: null,
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
    category: "hematology",
    priority: "routine",
    status: "collected",
    items: [],
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
    category: "chemistry",
    priority: "routine",
    status: "ordered",
    items: [],
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
    category: "chemistry",
    priority: "routine",
    status: "final",
    items: [
      {
        test_code: "TSH",
        test_name: "Thyroid Stimulating Hormone",
        specimen_type: "Blood",
        result_value: "2.1",
        result_unit: "mIU/L",
        reference_range: "0.4-4.0 mIU/L",
        abnormal_flag: "normal",
        interpretation: null,
      },
    ],
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
    category: "pathology",
    priority: "urgent",
    status: "draft",
    items: [],
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
    category: "immunology",
    priority: "routine",
    status: "draft",
    items: [],
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
    category: "chemistry",
    priority: "routine",
    status: "cancelled",
    items: [],
  },
];

function statusToOrderStatus(status: LabReportStatus): LabOrderStatus {
  if (status === "cancelled") return "cancelled";
  if (status === "draft") return "draft";
  if (status === "ordered") return "ordered";
  return "collected"; // "collected" and "final" both mean the order itself reached Collected
}

function statusToResultStatus(status: LabReportStatus): LabResultStatus | null {
  if (status === "final") return "final";
  if (status === "collected") return "draft"; // result entered but not finalized (mock-only nuance)
  return null;
}

let labReports: LabReportDetail[] = SEED.map((seed, index) => {
  const num = index + 1;
  const lab_report_id = `lab-${String(num).padStart(4, "0")}`;
  const orderedAt = atTime(dateOffset(seed.dayOffset), seed.nominalTime);
  const createdAt = new Date(orderedAt.getTime() - 30 * 60_000);
  const collectedAt =
    seed.status === "draft" || seed.status === "ordered"
      ? null
      : new Date(orderedAt.getTime() + 45 * 60_000);
  const reportedAt =
    seed.status === "final" ? new Date(orderedAt.getTime() + 3 * 60 * 60_000) : null;
  const updatedAt = reportedAt ?? collectedAt ?? createdAt;

  const items: LabTestItem[] = seed.items.map((item) => ({
    ...item,
    item_id: generateId("labitem"),
  }));

  const hasAbnormal = items.some((item) => item.abnormal_flag !== "normal");

  return {
    lab_report_id,
    organization_id: ORG_ID,
    report_number: `LAB-${60000 + num}`,
    patient_id: seed.patient_id,
    patient_name: seed.patient_name,
    patient_number: seed.patient_number,
    doctor_id: seed.doctor_id,
    doctor_name: seed.doctor_name,
    visit_id: seed.visit_id,
    visit_number: seed.visit_number,
    clinical_note_id: seed.clinical_note_id,
    clinical_note_number: seed.clinical_note_number,
    category: seed.category,
    priority: seed.priority,
    status: seed.status,
    test_summary: getTestSummary(items),
    ordered_at: orderedAt.toISOString(),
    collected_at: collectedAt ? collectedAt.toISOString() : null,
    created_at: createdAt.toISOString(),
    updated_at: updatedAt.toISOString(),
    order_status: statusToOrderStatus(seed.status),
    result_status: statusToResultStatus(seed.status),
    clinical_information: items.length > 0 ? "Routine screening as part of ongoing care." : null,
    interpretation:
      seed.status === "final"
        ? hasAbnormal
          ? "Some values outside reference range — see individual test interpretations. Clinical correlation recommended."
          : "All results within normal limits."
        : null,
    laboratory_name:
      seed.status === "final" || seed.status === "collected"
        ? "Riverside Clinical Laboratory"
        : null,
    reported_at: reportedAt ? reportedAt.toISOString() : null,
    notes: null,
    items,
    attachments:
      seed.status === "final"
        ? [
            {
              document_id: generateId("doc"),
              file_name: `Lab_Report_${dateOffset(seed.dayOffset)}.pdf`,
              attachment_type: "pdf",
              mime_type: "application/pdf",
              file_size_bytes: 156_000,
              uploaded_at: (reportedAt ?? updatedAt).toISOString(),
              description: "Signed laboratory report.",
            },
          ]
        : [],
    created_by_name: seed.doctor_name,
    updated_by_name: seed.doctor_name,
  };
});

// --- Repository: reads -----------------------------------------------

export interface LabReportListParams {
  search?: string;
  status?: LabReportStatus | "all";
  category?: LabReportCategory | "all";
  sortBy?:
    "report_number" | "patient_name" | "doctor_name" | "ordered_at" | "collected_at" | "status";
  sortDirection?: "asc" | "desc";
  page?: number;
  pageSize?: number;
}

function matchesSearch(report: LabReport, search: string): boolean {
  const needle = search.trim().toLowerCase();
  if (!needle) return true;
  return (
    report.report_number.toLowerCase().includes(needle) ||
    report.patient_name.toLowerCase().includes(needle) ||
    report.doctor_name.toLowerCase().includes(needle) ||
    report.visit_number.toLowerCase().includes(needle)
  );
}

function sortKey(report: LabReport, sortBy: NonNullable<LabReportListParams["sortBy"]>): string {
  return String(report[sortBy] ?? "");
}

function stripDetail(report: LabReportDetail): LabReport {
  return {
    lab_report_id: report.lab_report_id,
    organization_id: report.organization_id,
    report_number: report.report_number,
    patient_id: report.patient_id,
    patient_name: report.patient_name,
    patient_number: report.patient_number,
    doctor_id: report.doctor_id,
    doctor_name: report.doctor_name,
    visit_id: report.visit_id,
    visit_number: report.visit_number,
    clinical_note_id: report.clinical_note_id,
    clinical_note_number: report.clinical_note_number,
    category: report.category,
    priority: report.priority,
    status: report.status,
    test_summary: getTestSummary(report.items),
    ordered_at: report.ordered_at,
    collected_at: report.collected_at,
    created_at: report.created_at,
    updated_at: report.updated_at,
  };
}

export function listLabReports(
  params: LabReportListParams = {},
): Promise<PaginatedResponse<LabReport>> {
  const {
    search = "",
    status = "all",
    category = "all",
    sortBy = "ordered_at",
    sortDirection = "desc",
    page = 1,
    pageSize = 10,
  } = params;

  let filtered = labReports.filter((report) => matchesSearch(report, search));
  if (status !== "all") {
    filtered = filtered.filter((report) => report.status === status);
  }
  if (category !== "all") {
    filtered = filtered.filter((report) => report.category === category);
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

export function getLabReport(labReportId: string): Promise<LabReportDetail | null> {
  const found = labReports.find((report) => report.lab_report_id === labReportId) ?? null;
  return mockFetch(found, 300);
}

// Added for the Medical Documents module (`lib/mock/documents.ts`): a
// document's "Related Lab Report" section has no real backend FK to
// derive from (`MedicalDocument` only has `visit_id`/`appointment_id`,
// no `lab_order_id`) — this is the same shared-`visit_id` indirection
// already used elsewhere (e.g. Diagnosis via Visit). Mirrors
// `getClinicalNoteByVisitId()` exactly, just keyed by `visit_id` against
// this module's own array instead.
export function getLabReportByVisitId(visitId: string): Promise<LabReportDetail | null> {
  const found = labReports.find((report) => report.visit_id === visitId) ?? null;
  return mockFetch(found, 200);
}

// --- Repository: writes -------------------------------------------------
// `patient_id`/`doctor_id`/`visit_id` are deliberately absent from this
// input shape — mirroring the real `LabOrder`, they're derived from the
// selected clinical note (itself derived from the selected visit), not
// independently supplied.

export interface LabReportFormInput {
  patient_id: string;
  visit_id: string;
  doctor_id: string;
  clinical_note_id: string;
  category: LabReportCategory;
  priority: LabPriority;
  clinical_information: string;
  interpretation: string;
  items: LabTestItem[];
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
  const existing = labReports.find(
    (report) =>
      report.patient_id === input.patient_id ||
      report.doctor_id === input.doctor_id ||
      report.visit_id === input.visit_id ||
      report.clinical_note_id === input.clinical_note_id,
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

// "Save as Draft" leaves the report in its earliest state (mirrors the
// real `LabOrder` always starting Draft, no result yet). "Save as
// Final" collapses the full realistic multi-step lifecycle (Draft →
// Ordered → Collected, then a `LabResult` created → finalized) into one
// mock write — the real backend needs ~6 sequential calls to reach the
// same end state; this mock UI only exposes the two states this
// module's forms actually ask for (Draft/Final), not each intermediate
// transition as its own action.
export async function createLabReport(
  input: LabReportFormInput,
  status: "draft" | "final",
): Promise<LabReportDetail> {
  const id = generateId("lab");
  const nextNumber = 60000 + labReports.length + 1;
  const display = resolveDisplay(input);
  const now = new Date();
  const reportStatus: LabReportStatus = status === "final" ? "final" : "draft";

  const created: LabReportDetail = {
    lab_report_id: id,
    organization_id: ORG_ID,
    report_number: `LAB-${nextNumber}`,
    patient_id: input.patient_id,
    patient_name: display.patient_name,
    patient_number: display.patient_number,
    doctor_id: input.doctor_id,
    doctor_name: display.doctor_name,
    visit_id: input.visit_id,
    visit_number: display.visit_number,
    clinical_note_id: input.clinical_note_id,
    clinical_note_number: display.clinical_note_number,
    category: input.category,
    priority: input.priority,
    status: reportStatus,
    test_summary: getTestSummary(input.items),
    ordered_at: now.toISOString(),
    collected_at: status === "final" ? now.toISOString() : null,
    created_at: now.toISOString(),
    updated_at: now.toISOString(),
    order_status: statusToOrderStatus(reportStatus),
    result_status: statusToResultStatus(reportStatus),
    clinical_information: input.clinical_information || null,
    interpretation: input.interpretation || null,
    laboratory_name: status === "final" ? "Riverside Clinical Laboratory" : null,
    reported_at: status === "final" ? now.toISOString() : null,
    notes: null,
    items: input.items,
    attachments: [],
    created_by_name: display.doctor_name,
    updated_by_name: display.doctor_name,
  };

  labReports = [created, ...labReports];
  return mockFetch(created, 500);
}

export async function updateLabReport(
  labReportId: string,
  input: LabReportFormInput,
  status: "draft" | "final",
): Promise<LabReportDetail> {
  const index = labReports.findIndex((report) => report.lab_report_id === labReportId);
  const existing = labReports[index];
  if (!existing) {
    throw new Error(`Lab report ${labReportId} not found`);
  }
  if (!isLabReportEditable(existing.status)) {
    throw new Error(`Lab report ${labReportId} is not editable in its current status`);
  }

  const display = resolveDisplay(input);
  const now = new Date();
  const reportStatus: LabReportStatus = status === "final" ? "final" : "draft";

  const updated: LabReportDetail = {
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
    category: input.category,
    priority: input.priority,
    status: reportStatus,
    test_summary: getTestSummary(input.items),
    collected_at: status === "final" ? now.toISOString() : existing.collected_at,
    updated_at: now.toISOString(),
    order_status: statusToOrderStatus(reportStatus),
    result_status: statusToResultStatus(reportStatus),
    clinical_information: input.clinical_information || null,
    interpretation: input.interpretation || null,
    laboratory_name:
      status === "final" ? "Riverside Clinical Laboratory" : existing.laboratory_name,
    reported_at: status === "final" ? now.toISOString() : existing.reported_at,
    items: input.items,
  };

  labReports = [...labReports.slice(0, index), updated, ...labReports.slice(index + 1)];
  return mockFetch(updated, 500);
}

export function labReportToFormInput(report: LabReportDetail): LabReportFormInput {
  return {
    patient_id: report.patient_id,
    visit_id: report.visit_id,
    doctor_id: report.doctor_id,
    clinical_note_id: report.clinical_note_id,
    category: report.category,
    priority: report.priority,
    clinical_information: report.clinical_information ?? "",
    interpretation: report.interpretation ?? "",
    items: report.items,
  };
}
