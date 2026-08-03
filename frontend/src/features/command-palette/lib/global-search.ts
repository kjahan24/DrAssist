// Global search aggregation for the Command Palette
// (`features/command-palette/components/command-palette.tsx`). This is
// deliberately NOT a `lib/mock/*.ts` file — it introduces no new mock
// entities or seed data of its own. It only calls the already-existing
// `list*()` functions from every other completed module's mock
// repository (Patients, Appointments, Visits, Clinical Notes, SOAP
// Notes, Lab Reports, Prescriptions, Documents, Family Access,
// Notifications, Organization Members) and projects every match into
// one common `SearchResult` shape the palette can render uniformly —
// the same reasoning `lib/mock/timeline.ts` already documents for why
// it, too, has no seed data of its own.
//
// "Timeline Events" (the one category with no dedicated mock module of
// its own) is scoped to Patient Registration only, reusing the same
// patient rows already fetched for the "Patient" category — not the
// full per-patient event aggregation `lib/mock/timeline.ts` performs
// (visits/appointments/notes/labs/prescriptions/documents are already
// separately searchable as their own categories here, and allergies/
// medications/conditions live only on each patient's *detail* record,
// which would mean a detail fetch per patient on every keystroke). A
// command palette's own explicit design goal is to feel instant; a
// fan-out of a dozen-plus detail requests for a rarely-searched
// sub-field isn't a good trade against that.
//
// A real backend implementation of this feature would most likely be a
// single aggregated search endpoint (e.g. `GET /search?q=...`) doing
// this same fan-out server-side — swapping this file's body for that
// call later changes nothing about the hook or any component that
// consumes it.

import {
  listAppointments,
  getStatusLabel as getAppointmentStatusLabel,
} from "@/lib/mock/appointments";
import { listClinicalNotes } from "@/lib/mock/clinical-notes";
import { listDocuments } from "@/lib/mock/documents";
import { listFamilyMembers } from "@/lib/mock/family-members";
import { listLabReports } from "@/lib/mock/lab-reports";
import { listMembers } from "@/lib/mock/members";
import { listNotifications } from "@/lib/mock/notifications";
import { getFullName, listPatients } from "@/lib/mock/patients";
import { listPrescriptions } from "@/lib/mock/prescriptions";
import { listSoapNotes } from "@/lib/mock/soap-notes";
import { listVisits } from "@/lib/mock/visits";
import { formatDate } from "@/lib/format";

export type SearchEntityType =
  | "patient"
  | "appointment"
  | "visit"
  | "clinical_note"
  | "soap_note"
  | "lab_report"
  | "prescription"
  | "document"
  | "timeline_event"
  | "family_member"
  | "notification"
  | "organization_member";

export interface SearchResult {
  id: string;
  entity_type: SearchEntityType;
  title: string;
  subtitle: string;
  href: string;
}

// Per-category result cap — a command palette shows a handful of best
// matches per group, not an exhaustive paginated list (that's what each
// module's own list page is for).
const RESULTS_PER_CATEGORY = 5;

export async function searchAll(query: string): Promise<SearchResult[]> {
  const needle = query.trim();
  if (needle.length === 0) return [];

  const [
    patients,
    appointments,
    visits,
    clinicalNotes,
    soapNotes,
    labReports,
    prescriptions,
    documents,
    familyMembers,
    notifications,
    members,
  ] = await Promise.all([
    listPatients({ search: needle, pageSize: RESULTS_PER_CATEGORY }),
    listAppointments({ search: needle, pageSize: RESULTS_PER_CATEGORY }),
    listVisits({ search: needle, pageSize: RESULTS_PER_CATEGORY }),
    listClinicalNotes({ search: needle, pageSize: RESULTS_PER_CATEGORY }),
    listSoapNotes({ search: needle, pageSize: RESULTS_PER_CATEGORY }),
    listLabReports({ search: needle, pageSize: RESULTS_PER_CATEGORY }),
    listPrescriptions({ search: needle, pageSize: RESULTS_PER_CATEGORY }),
    listDocuments({ search: needle, pageSize: RESULTS_PER_CATEGORY }),
    listFamilyMembers({ search: needle, pageSize: RESULTS_PER_CATEGORY }),
    listNotifications({ search: needle, pageSize: RESULTS_PER_CATEGORY }),
    listMembers({ search: needle, pageSize: RESULTS_PER_CATEGORY }),
  ]);

  const results: SearchResult[] = [
    ...patients.items.map((patient): SearchResult => ({
      id: `patient-${patient.patient_id}`,
      entity_type: "patient",
      title: getFullName(patient),
      subtitle: `${patient.patient_number} · ${patient.phone}`,
      href: `/dashboard/patients/${patient.patient_id}`,
    })),
    ...appointments.items.map((appointment): SearchResult => ({
      id: `appointment-${appointment.appointment_id}`,
      entity_type: "appointment",
      title: `${appointment.patient_name} — Appointment`,
      subtitle: `${appointment.appointment_number} · ${formatDate(appointment.appointment_date)} · ${getAppointmentStatusLabel(appointment.status)}`,
      href: `/dashboard/appointments/${appointment.appointment_id}`,
    })),
    ...visits.items.map((visit): SearchResult => ({
      id: `visit-${visit.visit_id}`,
      entity_type: "visit",
      title: `${visit.patient_name} — Visit`,
      subtitle: `${visit.visit_number} · ${formatDate(visit.visit_date)}`,
      href: `/dashboard/visits/${visit.visit_id}`,
    })),
    ...clinicalNotes.items.map((note): SearchResult => ({
      id: `clinical-note-${note.clinical_note_id}`,
      entity_type: "clinical_note",
      title: `${note.patient_name} — Clinical Note`,
      subtitle: `${note.note_number} · ${formatDate(note.encounter_datetime)}`,
      href: `/dashboard/clinical-notes/${note.clinical_note_id}`,
    })),
    ...soapNotes.items.map((note): SearchResult => ({
      id: `soap-note-${note.soap_note_id}`,
      entity_type: "soap_note",
      title: `${note.patient_name} — SOAP Note`,
      subtitle: `${note.soap_number} · ${formatDate(note.created_at)}`,
      href: `/dashboard/soap-notes/${note.soap_note_id}`,
    })),
    ...labReports.items.map((report): SearchResult => ({
      id: `lab-report-${report.lab_report_id}`,
      entity_type: "lab_report",
      title: `${report.patient_name} — Lab Report`,
      subtitle: `${report.report_number} · ${report.test_summary}`,
      href: `/dashboard/lab-reports/${report.lab_report_id}`,
    })),
    ...prescriptions.items.map((prescription): SearchResult => ({
      id: `prescription-${prescription.prescription_id}`,
      entity_type: "prescription",
      title: `${prescription.patient_name} — Prescription`,
      subtitle: `${prescription.prescription_number} · ${formatDate(prescription.prescription_date)}`,
      href: `/dashboard/prescriptions/${prescription.prescription_id}`,
    })),
    ...documents.items.map((document): SearchResult => ({
      id: `document-${document.document_id}`,
      entity_type: "document",
      title: document.title,
      subtitle: `${document.patient_name} · ${document.document_number}`,
      href: `/dashboard/documents/${document.document_id}`,
    })),
    ...familyMembers.items.map((member): SearchResult => ({
      id: `family-member-${member.family_access_id}`,
      entity_type: "family_member",
      title: `${member.member_name} — Family Access`,
      subtitle: `for ${member.patient_name}`,
      href: `/dashboard/family/${member.family_access_id}`,
    })),
    ...notifications.items.map((notification): SearchResult => ({
      id: `notification-${notification.notification_id}`,
      entity_type: "notification",
      title: notification.title,
      subtitle: notification.message,
      href: notification.quick_action_href ?? "/dashboard/notifications",
    })),
    ...members.items.map((member): SearchResult => ({
      id: `organization-member-${member.member_id}`,
      entity_type: "organization_member",
      title: member.full_name,
      subtitle: member.department_name
        ? `${member.role_name} · ${member.department_name}`
        : member.role_name,
      href: "/dashboard/organization/members",
    })),
    // "Timeline Events" — see this file's own docstring for why this is
    // scoped to Patient Registration, reusing the patient rows already
    // fetched above rather than a separate query.
    ...patients.items.map((patient): SearchResult => ({
      id: `timeline-event-${patient.patient_id}`,
      entity_type: "timeline_event",
      title: `${getFullName(patient)} — Patient Registered`,
      subtitle: `Registered ${formatDate(patient.created_at)} · View full timeline`,
      href: `/dashboard/timeline/${patient.patient_id}`,
    })),
  ];

  return results;
}
