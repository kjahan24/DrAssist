// Temporary frontend mock repository for the Personal Health Timeline
// (`app/(dashboard)/dashboard/timeline/*`). No backend API is consumed
// anywhere in this module. Unlike every other `lib/mock/*.ts` file, this
// one has no seed data and no real backend module of its own to mirror
// field-for-field — "Personal Health Timeline" is a read-only,
// cross-module aggregation view, not its own aggregate. It works
// entirely by calling the already-existing `list*()` functions from
// every other completed module's mock repository (Patients,
// Appointments, Visits, Clinical Notes, SOAP Notes, Lab Reports,
// Prescriptions, Documents), filtering each result down to one patient,
// and projecting every record into one common `HealthTimelineEvent`
// shape the UI can render uniformly. A real backend implementation of
// this feature would most likely do the same aggregation server-side
// (a single `GET /timeline?patient_id=...` endpoint joining across
// those same modules) — swapping this file's body for that call later
// changes nothing about `features/timeline/hooks/use-timeline.ts` or any
// component.
//
// Every field on `HealthTimelineEvent` is either copied directly from an
// existing, already-modeled list-row field (title/summary/doctor_name/
// timestamps/status), or a link derived from a real FK those list rows
// already carry (`visit_id`, `clinical_note_id`, `appointment_id`, ...) —
// no new seed data, no new invented entities. Two exceptions, called out
// because they don't map to anything modeled elsewhere:
//   - `related` — the "Related entities" list shown in
//     `TimelineDetailsPanel`. Computed by cross-referencing the other
//     already-fetched per-patient arrays in memory (e.g. an Appointment
//     event's related Visit is found via `visits.find(v => v.appointment_id
//     === appointment.appointment_id)`), the same reverse-indirection
//     pattern already established for "Related Lab Report"/"Related
//     Prescription" in `lib/mock/documents.ts`.
//   - `attachment_count` — not a real field anywhere; computed as how
//     many of the patient's own Medical Documents share the same
//     `visit_id` as the event, for the Details Panel's "Attachments
//     Summary".
//
// Some event types (Clinical Note, SOAP Note, Prescription) have no
// descriptive text on their *list-row* shape (only their `*Detail` type
// does, e.g. `chief_complaint_summary`). Rather than issuing a detail
// fetch per record — which would turn one timeline load into dozens of
// requests — `summary` is left `null` for those event types and the
// card falls back to title + status, matching what a real aggregated
// timeline endpoint would most plausibly return too (a summary/preview
// field, not the full record body).

import {
  getStatusLabel as getAppointmentStatusLabel,
  getTypeLabel as getAppointmentTypeLabel,
  listAppointments,
  type Appointment,
} from "@/lib/mock/appointments";
import {
  getClinicalNoteStatusLabel,
  getClinicalNoteTypeLabel,
  listClinicalNotes,
  type ClinicalNote,
} from "@/lib/mock/clinical-notes";
import {
  getDocumentCategoryLabel,
  getDocumentStatusLabel,
  listDocuments,
  type MedicalDocument,
} from "@/lib/mock/documents";
import {
  getLabReportCategoryLabel,
  getLabReportStatusLabel,
  listLabReports,
  type LabReport,
} from "@/lib/mock/lab-reports";
import {
  getFullName,
  getPatient,
  type Allergy,
  type MedicalCondition,
  type Medication,
  type PatientDetail,
} from "@/lib/mock/patients";
import {
  getPrescriptionStatusLabel,
  listPrescriptions,
  type Prescription,
} from "@/lib/mock/prescriptions";
import { getSoapNoteStatusLabel, listSoapNotes, type SOAPNote } from "@/lib/mock/soap-notes";
import { getVisitStatusLabel, getVisitTypeLabel, listVisits, type Visit } from "@/lib/mock/visits";

const MIN_LATENCY_MS = 350;

function mockFetch<T>(value: T, latencyMs: number = MIN_LATENCY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), latencyMs));
}

// A generous upper bound well above any module's actual seed count, so
// every list call below returns every record for every patient in one
// page — this module then does its own per-patient filtering in memory.
const FETCH_ALL_PAGE_SIZE = 500;

// --- Event type -----------------------------------------------------

export type TimelineEventType =
  | "patient_registration"
  | "appointment"
  | "visit"
  | "clinical_note"
  | "soap_note"
  | "lab_report"
  | "prescription"
  | "document"
  | "allergy"
  | "medication"
  | "medical_condition";

export const TIMELINE_EVENT_TYPE_OPTIONS: { label: string; value: TimelineEventType }[] = [
  { label: "Patient Registration", value: "patient_registration" },
  { label: "Appointment", value: "appointment" },
  { label: "Visit", value: "visit" },
  { label: "Clinical Note", value: "clinical_note" },
  { label: "SOAP Note", value: "soap_note" },
  { label: "Lab Report", value: "lab_report" },
  { label: "Prescription", value: "prescription" },
  { label: "Medical Document", value: "document" },
  { label: "Allergy", value: "allergy" },
  { label: "Medication", value: "medication" },
  { label: "Medical Condition", value: "medical_condition" },
];

export function getTimelineEventTypeLabel(type: TimelineEventType): string {
  return TIMELINE_EVENT_TYPE_OPTIONS.find((option) => option.value === type)?.label ?? type;
}

export interface TimelineRelatedLink {
  label: string;
  href: string;
}

export interface HealthTimelineEvent {
  event_id: string;
  event_type: TimelineEventType;
  title: string;
  occurred_at: string; // ISO 8601 datetime — always full precision, see toDateTime()
  patient_id: string;
  patient_name: string;
  patient_number: string;
  doctor_name: string | null;
  summary: string | null;
  status_label: string | null;
  visit_id: string | null;
  visit_number: string | null;
  related: TimelineRelatedLink[];
  quick_action: TimelineRelatedLink;
  attachment_count: number;
}

// --- Helpers ----------------------------------------------------------

function toDateTime(dateOnly: string, time = "09:00:00"): string {
  return new Date(`${dateOnly}T${time}`).toISOString();
}

function capitalize(value: string): string {
  const first = value.charAt(0);
  return first === "" ? value : `${first.toUpperCase()}${value.slice(1).replace(/_/g, " ")}`;
}

function countAttachments(documents: MedicalDocument[], visitId: string | null): number {
  if (!visitId) return 0;
  return documents.filter((document) => document.visit_id === visitId).length;
}

// --- Per-type projections ----------------------------------------------
// Each function below takes one already patient-filtered record plus
// whatever sibling arrays it needs to resolve `related` links, and
// returns one `HealthTimelineEvent`.

function fromRegistration(patient: PatientDetail): HealthTimelineEvent {
  return {
    event_id: `tl-reg-${patient.patient_id}`,
    event_type: "patient_registration",
    title: "Patient Registered",
    occurred_at: patient.created_at,
    patient_id: patient.patient_id,
    patient_name: getFullName(patient),
    patient_number: patient.patient_number,
    doctor_name: null,
    summary: `Registered as ${patient.patient_number}.`,
    status_label: patient.status === "active" ? "Active" : "Inactive",
    visit_id: null,
    visit_number: null,
    related: [],
    quick_action: {
      label: "View Patient Record",
      href: `/dashboard/patients/${patient.patient_id}`,
    },
    attachment_count: 0,
  };
}

function fromAppointment(appointment: Appointment, visits: Visit[]): HealthTimelineEvent {
  const relatedVisit = visits.find((visit) => visit.appointment_id === appointment.appointment_id);
  const related: TimelineRelatedLink[] = relatedVisit
    ? [
        {
          label: `Visit ${relatedVisit.visit_number}`,
          href: `/dashboard/visits/${relatedVisit.visit_id}`,
        },
      ]
    : [];

  return {
    event_id: `tl-appt-${appointment.appointment_id}`,
    event_type: "appointment",
    title: `${getAppointmentTypeLabel(appointment.appointment_type)} Appointment`,
    occurred_at: toDateTime(appointment.appointment_date, `${appointment.start_time}:00`),
    patient_id: appointment.patient_id,
    patient_name: appointment.patient_name,
    patient_number: appointment.patient_number,
    doctor_name: appointment.doctor_name,
    summary: appointment.reason_for_visit,
    status_label: getAppointmentStatusLabel(appointment.status),
    visit_id: relatedVisit?.visit_id ?? null,
    visit_number: relatedVisit?.visit_number ?? null,
    related,
    quick_action: {
      label: "View Appointment",
      href: `/dashboard/appointments/${appointment.appointment_id}`,
    },
    attachment_count: 0,
  };
}

function fromVisit(
  visit: Visit,
  clinicalNotes: ClinicalNote[],
  soapNotes: SOAPNote[],
  labReports: LabReport[],
  prescriptions: Prescription[],
  documents: MedicalDocument[],
): HealthTimelineEvent {
  const related: TimelineRelatedLink[] = [];
  if (visit.appointment_id) {
    related.push({
      label: "Source Appointment",
      href: `/dashboard/appointments/${visit.appointment_id}`,
    });
  }
  const note = clinicalNotes.find((n) => n.visit_id === visit.visit_id);
  if (note)
    related.push({
      label: `Clinical Note ${note.note_number}`,
      href: `/dashboard/clinical-notes/${note.clinical_note_id}`,
    });
  const soap = soapNotes.find((s) => s.visit_id === visit.visit_id);
  if (soap)
    related.push({
      label: `SOAP Note ${soap.soap_number}`,
      href: `/dashboard/soap-notes/${soap.soap_note_id}`,
    });
  const lab = labReports.find((l) => l.visit_id === visit.visit_id);
  if (lab)
    related.push({
      label: `Lab Report ${lab.report_number}`,
      href: `/dashboard/lab-reports/${lab.lab_report_id}`,
    });
  const prescription = prescriptions.find((p) => p.visit_id === visit.visit_id);
  if (prescription) {
    related.push({
      label: `Prescription ${prescription.prescription_number}`,
      href: `/dashboard/prescriptions/${prescription.prescription_id}`,
    });
  }

  return {
    event_id: `tl-visit-${visit.visit_id}`,
    event_type: "visit",
    title: `${getVisitTypeLabel(visit.visit_type)} Visit`,
    occurred_at: toDateTime(visit.visit_date),
    patient_id: visit.patient_id,
    patient_name: visit.patient_name,
    patient_number: visit.patient_number,
    doctor_name: visit.doctor_name,
    summary: visit.chief_complaint_summary,
    status_label: getVisitStatusLabel(visit.visit_status),
    visit_id: visit.visit_id,
    visit_number: visit.visit_number,
    related,
    quick_action: { label: "View Visit", href: `/dashboard/visits/${visit.visit_id}` },
    attachment_count: countAttachments(documents, visit.visit_id),
  };
}

function fromClinicalNote(
  note: ClinicalNote,
  soapNotes: SOAPNote[],
  prescriptions: Prescription[],
  documents: MedicalDocument[],
): HealthTimelineEvent {
  const related: TimelineRelatedLink[] = [
    { label: `Visit ${note.visit_number}`, href: `/dashboard/visits/${note.visit_id}` },
  ];
  const soap = soapNotes.find((s) => s.clinical_note_id === note.clinical_note_id);
  if (soap)
    related.push({
      label: `SOAP Note ${soap.soap_number}`,
      href: `/dashboard/soap-notes/${soap.soap_note_id}`,
    });
  const prescription = prescriptions.find((p) => p.clinical_note_id === note.clinical_note_id);
  if (prescription) {
    related.push({
      label: `Prescription ${prescription.prescription_number}`,
      href: `/dashboard/prescriptions/${prescription.prescription_id}`,
    });
  }

  return {
    event_id: `tl-cn-${note.clinical_note_id}`,
    event_type: "clinical_note",
    title: `${getClinicalNoteTypeLabel(note.note_type)} Clinical Note`,
    occurred_at: note.encounter_datetime,
    patient_id: note.patient_id,
    patient_name: note.patient_name,
    patient_number: note.patient_number,
    doctor_name: note.doctor_name,
    summary: null,
    status_label: getClinicalNoteStatusLabel(note.status),
    visit_id: note.visit_id,
    visit_number: note.visit_number,
    related,
    quick_action: {
      label: "View Clinical Note",
      href: `/dashboard/clinical-notes/${note.clinical_note_id}`,
    },
    attachment_count: countAttachments(documents, note.visit_id),
  };
}

function fromSoapNote(note: SOAPNote, documents: MedicalDocument[]): HealthTimelineEvent {
  return {
    event_id: `tl-soap-${note.soap_note_id}`,
    event_type: "soap_note",
    title: "SOAP Note",
    occurred_at: note.created_at,
    patient_id: note.patient_id,
    patient_name: note.patient_name,
    patient_number: note.patient_number,
    doctor_name: note.doctor_name,
    summary: null,
    status_label: getSoapNoteStatusLabel(note.status),
    visit_id: note.visit_id,
    visit_number: note.visit_number,
    related: [
      { label: `Visit ${note.visit_number}`, href: `/dashboard/visits/${note.visit_id}` },
      {
        label: `Clinical Note ${note.clinical_note_number}`,
        href: `/dashboard/clinical-notes/${note.clinical_note_id}`,
      },
    ],
    quick_action: { label: "View SOAP Note", href: `/dashboard/soap-notes/${note.soap_note_id}` },
    attachment_count: countAttachments(documents, note.visit_id),
  };
}

function fromLabReport(report: LabReport, documents: MedicalDocument[]): HealthTimelineEvent {
  return {
    event_id: `tl-lab-${report.lab_report_id}`,
    event_type: "lab_report",
    title: `${getLabReportCategoryLabel(report.category)} Lab Report`,
    occurred_at: report.ordered_at,
    patient_id: report.patient_id,
    patient_name: report.patient_name,
    patient_number: report.patient_number,
    doctor_name: report.doctor_name,
    summary: report.test_summary,
    status_label: getLabReportStatusLabel(report.status),
    visit_id: report.visit_id,
    visit_number: report.visit_number,
    related: [
      { label: `Visit ${report.visit_number}`, href: `/dashboard/visits/${report.visit_id}` },
      {
        label: `Clinical Note ${report.clinical_note_number}`,
        href: `/dashboard/clinical-notes/${report.clinical_note_id}`,
      },
    ],
    quick_action: {
      label: "View Lab Report",
      href: `/dashboard/lab-reports/${report.lab_report_id}`,
    },
    attachment_count: countAttachments(documents, report.visit_id),
  };
}

function fromPrescription(
  prescription: Prescription,
  documents: MedicalDocument[],
): HealthTimelineEvent {
  return {
    event_id: `tl-rx-${prescription.prescription_id}`,
    event_type: "prescription",
    title: "Prescription",
    occurred_at: prescription.created_at,
    patient_id: prescription.patient_id,
    patient_name: prescription.patient_name,
    patient_number: prescription.patient_number,
    doctor_name: prescription.doctor_name,
    summary: null,
    status_label: getPrescriptionStatusLabel(prescription.status),
    visit_id: prescription.visit_id,
    visit_number: prescription.visit_number,
    related: [
      {
        label: `Visit ${prescription.visit_number}`,
        href: `/dashboard/visits/${prescription.visit_id}`,
      },
      {
        label: `Clinical Note ${prescription.clinical_note_number}`,
        href: `/dashboard/clinical-notes/${prescription.clinical_note_id}`,
      },
    ],
    quick_action: {
      label: "View Prescription",
      href: `/dashboard/prescriptions/${prescription.prescription_id}`,
    },
    attachment_count: countAttachments(documents, prescription.visit_id),
  };
}

function fromDocument(document: MedicalDocument): HealthTimelineEvent {
  const related: TimelineRelatedLink[] = document.visit_id
    ? [{ label: `Visit ${document.visit_number}`, href: `/dashboard/visits/${document.visit_id}` }]
    : [];

  return {
    event_id: `tl-doc-${document.document_id}`,
    event_type: "document",
    title: document.title,
    occurred_at: document.uploaded_at,
    patient_id: document.patient_id,
    patient_name: document.patient_name,
    patient_number: document.patient_number,
    doctor_name: null,
    summary: `${getDocumentCategoryLabel(document.category)} · Uploaded by ${document.uploaded_by_name}`,
    status_label: getDocumentStatusLabel(document.status),
    visit_id: document.visit_id,
    visit_number: document.visit_number,
    related,
    quick_action: { label: "View Document", href: `/dashboard/documents/${document.document_id}` },
    attachment_count: 0,
  };
}

function fromAllergy(patient: PatientDetail, allergy: Allergy): HealthTimelineEvent {
  return {
    event_id: `tl-alg-${allergy.allergy_id}`,
    event_type: "allergy",
    title: `Allergy — ${allergy.allergen_name}`,
    occurred_at: toDateTime(allergy.onset_date ?? patient.created_at.slice(0, 10)),
    patient_id: patient.patient_id,
    patient_name: getFullName(patient),
    patient_number: patient.patient_number,
    doctor_name: null,
    summary: allergy.reaction,
    status_label: capitalize(allergy.status),
    visit_id: null,
    visit_number: null,
    related: [],
    quick_action: {
      label: "View Patient Record",
      href: `/dashboard/patients/${patient.patient_id}`,
    },
    attachment_count: 0,
  };
}

function fromMedication(patient: PatientDetail, medication: Medication): HealthTimelineEvent {
  return {
    event_id: `tl-med-${medication.medication_id}`,
    event_type: "medication",
    title: `Medication — ${medication.medication_name}`,
    occurred_at: toDateTime(medication.start_date),
    patient_id: patient.patient_id,
    patient_name: getFullName(patient),
    patient_number: patient.patient_number,
    doctor_name: null,
    summary: `${medication.dosage} ${medication.dosage_unit} · ${medication.frequency}`,
    status_label: medication.is_current ? "Current" : "Discontinued",
    visit_id: null,
    visit_number: null,
    related: [],
    quick_action: {
      label: "View Patient Record",
      href: `/dashboard/patients/${patient.patient_id}`,
    },
    attachment_count: 0,
  };
}

function fromCondition(patient: PatientDetail, condition: MedicalCondition): HealthTimelineEvent {
  return {
    event_id: `tl-cond-${condition.condition_id}`,
    event_type: "medical_condition",
    title: `Condition — ${condition.condition_name}`,
    occurred_at: toDateTime(condition.diagnosis_date),
    patient_id: patient.patient_id,
    patient_name: getFullName(patient),
    patient_number: patient.patient_number,
    doctor_name: null,
    summary: condition.category,
    status_label: capitalize(condition.status),
    visit_id: null,
    visit_number: null,
    related: [],
    quick_action: {
      label: "View Patient Record",
      href: `/dashboard/patients/${patient.patient_id}`,
    },
    attachment_count: 0,
  };
}

// --- Aggregation --------------------------------------------------------

// The only async function in this file — fetches every source module's
// full list in parallel, filters each down to one patient, projects
// every record into a `HealthTimelineEvent`, and returns them sorted
// newest-first. Returns `[]` for an unknown patient id rather than
// throwing — the page composer resolves "patient not found" itself via
// `usePatient()`.
export async function getPatientTimeline(patientId: string): Promise<HealthTimelineEvent[]> {
  const [
    patient,
    appointmentsPage,
    visitsPage,
    clinicalNotesPage,
    soapNotesPage,
    labReportsPage,
    prescriptionsPage,
    documentsPage,
  ] = await Promise.all([
    getPatient(patientId),
    listAppointments({ pageSize: FETCH_ALL_PAGE_SIZE }),
    listVisits({ pageSize: FETCH_ALL_PAGE_SIZE }),
    listClinicalNotes({ pageSize: FETCH_ALL_PAGE_SIZE }),
    listSoapNotes({ pageSize: FETCH_ALL_PAGE_SIZE }),
    listLabReports({ pageSize: FETCH_ALL_PAGE_SIZE }),
    listPrescriptions({ pageSize: FETCH_ALL_PAGE_SIZE }),
    listDocuments({ pageSize: FETCH_ALL_PAGE_SIZE }),
  ]);

  if (!patient) return [];

  const appointments = appointmentsPage.items.filter((item) => item.patient_id === patientId);
  const visits = visitsPage.items.filter((item) => item.patient_id === patientId);
  const clinicalNotes = clinicalNotesPage.items.filter((item) => item.patient_id === patientId);
  const soapNotes = soapNotesPage.items.filter((item) => item.patient_id === patientId);
  const labReports = labReportsPage.items.filter((item) => item.patient_id === patientId);
  const prescriptions = prescriptionsPage.items.filter((item) => item.patient_id === patientId);
  const documents = documentsPage.items.filter((item) => item.patient_id === patientId);

  const events: HealthTimelineEvent[] = [
    fromRegistration(patient),
    ...appointments.map((appointment) => fromAppointment(appointment, visits)),
    ...visits.map((visit) =>
      fromVisit(visit, clinicalNotes, soapNotes, labReports, prescriptions, documents),
    ),
    ...clinicalNotes.map((note) => fromClinicalNote(note, soapNotes, prescriptions, documents)),
    ...soapNotes.map((note) => fromSoapNote(note, documents)),
    ...labReports.map((report) => fromLabReport(report, documents)),
    ...prescriptions.map((prescription) => fromPrescription(prescription, documents)),
    ...documents.map((document) => fromDocument(document)),
    ...patient.allergies.map((allergy) => fromAllergy(patient, allergy)),
    ...patient.medications.map((medication) => fromMedication(patient, medication)),
    ...patient.medical_conditions.map((condition) => fromCondition(patient, condition)),
  ];

  events.sort((a, b) => b.occurred_at.localeCompare(a.occurred_at));

  return mockFetch(events, 500);
}

// --- Client-side filter/search/group helpers ----------------------------
// Deliberately synchronous and pure (no mock latency) — the timeline
// page fetches the patient's full event list exactly once via
// `getPatientTimeline()`, then slices it different ways locally as the
// user types a search or changes a filter, instead of refetching.

export interface TimelineFilterState {
  search?: string;
  eventType?: TimelineEventType | "all";
  doctorName?: string | "all";
  visitId?: string | "all";
  status?: string | "all";
  dateFrom?: string; // ISO date "YYYY-MM-DD"
  dateTo?: string; // ISO date "YYYY-MM-DD"
}

export function filterTimelineEvents(
  events: HealthTimelineEvent[],
  filters: TimelineFilterState,
): HealthTimelineEvent[] {
  const search = (filters.search ?? "").trim().toLowerCase();

  return events.filter((event) => {
    if (search) {
      const haystack =
        `${event.title} ${event.summary ?? ""} ${event.doctor_name ?? ""}`.toLowerCase();
      if (!haystack.includes(search)) return false;
    }
    if (
      filters.eventType &&
      filters.eventType !== "all" &&
      event.event_type !== filters.eventType
    ) {
      return false;
    }
    if (
      filters.doctorName &&
      filters.doctorName !== "all" &&
      event.doctor_name !== filters.doctorName
    ) {
      return false;
    }
    if (filters.visitId && filters.visitId !== "all" && event.visit_id !== filters.visitId) {
      return false;
    }
    if (filters.status && filters.status !== "all" && event.status_label !== filters.status) {
      return false;
    }
    if (filters.dateFrom && event.occurred_at.slice(0, 10) < filters.dateFrom) return false;
    if (filters.dateTo && event.occurred_at.slice(0, 10) > filters.dateTo) return false;
    return true;
  });
}

export interface TimelineFilterOptions {
  doctors: string[];
  visits: { visit_id: string; visit_number: string }[];
  statuses: string[];
}

// Computed from the *unfiltered* event list so every dropdown always
// offers every option the patient's own timeline actually contains,
// regardless of which filters are currently active.
export function getTimelineFilterOptions(events: HealthTimelineEvent[]): TimelineFilterOptions {
  const doctors = Array.from(
    new Set(
      events.map((event) => event.doctor_name).filter((name): name is string => Boolean(name)),
    ),
  ).sort();

  const visitMap = new Map<string, string>();
  for (const event of events) {
    if (event.visit_id && event.visit_number) visitMap.set(event.visit_id, event.visit_number);
  }
  const visits = Array.from(visitMap.entries())
    .map(([visit_id, visit_number]) => ({ visit_id, visit_number }))
    .sort((a, b) => a.visit_number.localeCompare(b.visit_number));

  const statuses = Array.from(
    new Set(
      events
        .map((event) => event.status_label)
        .filter((status): status is string => Boolean(status)),
    ),
  ).sort();

  return { doctors, visits, statuses };
}

export interface TimelineDateGroupData {
  dateKey: string; // "YYYY-MM-DD"
  events: HealthTimelineEvent[];
}

// Assumes `events` is already sorted newest-first (as `getPatientTimeline`
// returns it) — a JS `Map`'s iteration order matches insertion order, so
// groups come out newest-date-first too.
export function groupEventsByDate(events: HealthTimelineEvent[]): TimelineDateGroupData[] {
  const groups = new Map<string, HealthTimelineEvent[]>();
  for (const event of events) {
    const key = event.occurred_at.slice(0, 10);
    const bucket = groups.get(key);
    if (bucket) {
      bucket.push(event);
    } else {
      groups.set(key, [event]);
    }
  }
  return Array.from(groups.entries()).map(([dateKey, dateEvents]) => ({
    dateKey,
    events: dateEvents,
  }));
}
