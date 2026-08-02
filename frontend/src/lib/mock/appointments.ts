// Temporary frontend mock repository for Appointment Management
// (`app/(dashboard)/dashboard/appointments/*`). No backend API is
// consumed anywhere in this module — every function below reads from and
// writes to an in-memory array, standing in for the backend Appointment
// module (`app.modules.appointment`) until its REST endpoints are wired
// up (its router currently registers zero routes).
//
// Field names are grounded in the real domain entity
// (`app.modules.appointment.domain.entities.Appointment`):
// `patient_id, doctor_id, appointment_number, appointment_date, start_time,
// end_time, appointment_type, status, reason_for_visit, notes,
// booked_by_user_id, visit_id, checked_in_at, completed_at, cancelled_at`.
// `status` (`AppointmentStatus`) and `appointment_type` (`AppointmentType`)
// enums below match `domain/enums.py` verbatim, including the real allowed
// status transitions (`_ALLOWED_TRANSITIONS`), reproduced in
// `getAllowedTransitions()` so "Quick Actions" on the detail page only
// ever offers a transition the real backend would also accept.
//
// Two things here are frontend-only inventions with no backend
// counterpart, called out explicitly because they can't be grounded in
// anything real:
//   - `patient_name`/`patient_number`/`doctor_name`/`department` are
//     denormalized display fields. The real entity only stores
//     `patient_id`/`doctor_id`; a real list endpoint would need to either
//     join across modules or accept a second round-trip, so this mirrors
//     the *simplest* realistic shape a real API might return.
//     `department` in particular has no backend linkage at all yet — see
//     `lib/mock/doctors.ts`'s docstring.
//   - `status_history` (`AppointmentStatusHistoryEntry[]`) — the backend
//     only fires a single `AppointmentStatusChanged` domain event per
//     transition; there's no queryable transition log. This is invented
//     for the "Status History" detail section and generated deterministically
//     from each seeded appointment's final status.

import type { PaginatedResponse } from "@/types";

const MIN_LATENCY_MS = 350;

function mockFetch<T>(value: T, latencyMs: number = MIN_LATENCY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), latencyMs));
}

function generateId(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

// --- Enums (verbatim from `app.modules.appointment.domain.enums`) -----

export type AppointmentStatus =
  "scheduled" | "confirmed" | "checked_in" | "in_progress" | "completed" | "cancelled" | "no_show";

export type AppointmentType =
  "consultation" | "follow_up" | "emergency" | "telemedicine" | "procedure";

export const APPOINTMENT_STATUS_OPTIONS: { label: string; value: AppointmentStatus }[] = [
  { label: "Scheduled", value: "scheduled" },
  { label: "Confirmed", value: "confirmed" },
  { label: "Checked In", value: "checked_in" },
  { label: "In Progress", value: "in_progress" },
  { label: "Completed", value: "completed" },
  { label: "Cancelled", value: "cancelled" },
  { label: "No Show", value: "no_show" },
];

export const APPOINTMENT_TYPE_OPTIONS: { label: string; value: AppointmentType }[] = [
  { label: "Consultation", value: "consultation" },
  { label: "Follow-up", value: "follow_up" },
  { label: "Emergency", value: "emergency" },
  { label: "Telemedicine", value: "telemedicine" },
  { label: "Procedure", value: "procedure" },
];

export function getStatusLabel(status: AppointmentStatus): string {
  return APPOINTMENT_STATUS_OPTIONS.find((option) => option.value === status)?.label ?? status;
}

export function getTypeLabel(type: AppointmentType): string {
  return APPOINTMENT_TYPE_OPTIONS.find((option) => option.value === type)?.label ?? type;
}

// Mirrors `Appointment._ALLOWED_TRANSITIONS` exactly — `completed`,
// `cancelled`, and `no_show` are terminal (no outgoing transitions).
const ALLOWED_TRANSITIONS: Record<AppointmentStatus, AppointmentStatus[]> = {
  scheduled: ["confirmed", "checked_in", "cancelled", "no_show"],
  confirmed: ["checked_in", "cancelled", "no_show"],
  checked_in: ["in_progress", "completed", "cancelled"],
  in_progress: ["completed", "cancelled"],
  completed: [],
  cancelled: [],
  no_show: [],
};

export function getAllowedTransitions(status: AppointmentStatus): AppointmentStatus[] {
  return ALLOWED_TRANSITIONS[status];
}

// --- Booking slots ------------------------------------------------------
// No slot-generation logic exists in the real backend yet — the closest
// real concept is `app.modules.schedule.domain.entities.DoctorSchedule`'s
// `slot_duration_minutes`. Fixed 30-minute slots across a standard clinic
// day stand in for that until per-doctor schedules are wired up here too.

export const DEFAULT_SLOT_DURATION_MINUTES = 30;

export const TIME_SLOTS: string[] = Array.from({ length: 20 }, (_, index) => {
  const totalMinutes = 8 * 60 + index * DEFAULT_SLOT_DURATION_MINUTES; // 08:00–17:30
  const hours = String(Math.floor(totalMinutes / 60)).padStart(2, "0");
  const minutes = String(totalMinutes % 60).padStart(2, "0");
  return `${hours}:${minutes}`;
});

export function computeEndTime(
  startTime: string,
  durationMinutes: number = DEFAULT_SLOT_DURATION_MINUTES,
): string {
  const [hoursText, minutesText] = startTime.split(":");
  const totalMinutes = Number(hoursText) * 60 + Number(minutesText) + durationMinutes;
  const hours = String(Math.floor(totalMinutes / 60) % 24).padStart(2, "0");
  const minutes = String(totalMinutes % 60).padStart(2, "0");
  return `${hours}:${minutes}`;
}

// --- Core shapes ---------------------------------------------------------

export interface Appointment {
  appointment_id: string;
  organization_id: string;
  appointment_number: string;
  patient_id: string;
  patient_name: string;
  patient_number: string;
  doctor_id: string;
  doctor_name: string;
  department: string;
  appointment_date: string; // ISO 8601 date ("YYYY-MM-DD")
  start_time: string; // "HH:mm"
  end_time: string; // "HH:mm"
  appointment_type: AppointmentType;
  status: AppointmentStatus;
  reason_for_visit: string | null;
  created_at: string; // ISO 8601
}

export interface AppointmentStatusHistoryEntry {
  status: AppointmentStatus;
  changed_at: string; // ISO 8601
  note?: string | null;
}

export interface AppointmentDetail extends Appointment {
  notes: string | null;
  booked_by_name: string | null;
  checked_in_at: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  status_history: AppointmentStatusHistoryEntry[];
}

export function getPatientInitials(appointment: Pick<Appointment, "patient_name">): string {
  return appointment.patient_name
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

function combineDateTime(isoDate: string, time: string): Date {
  return new Date(`${isoDate}T${time}:00`);
}

function buildStatusHistory(
  finalStatus: AppointmentStatus,
  createdAt: Date,
  appointmentStart: Date,
  appointmentEnd: Date,
): AppointmentStatusHistoryEntry[] {
  const history: AppointmentStatusHistoryEntry[] = [
    { status: "scheduled", changed_at: createdAt.toISOString() },
  ];

  if (finalStatus === "scheduled") return history;

  if (finalStatus === "cancelled") {
    const cancelledAt = new Date(createdAt.getTime() + 4 * 60 * 60_000);
    history.push({
      status: "cancelled",
      changed_at: cancelledAt.toISOString(),
      note: "Cancelled by front desk.",
    });
    return history;
  }

  history.push({
    status: "confirmed",
    changed_at: new Date(createdAt.getTime() + 4 * 60 * 60_000).toISOString(),
  });
  if (finalStatus === "confirmed") return history;

  if (finalStatus === "no_show") {
    history.push({
      status: "no_show",
      changed_at: new Date(appointmentStart.getTime() + 15 * 60_000).toISOString(),
      note: "Patient did not arrive for their appointment.",
    });
    return history;
  }

  history.push({
    status: "checked_in",
    changed_at: new Date(appointmentStart.getTime() - 10 * 60_000).toISOString(),
  });
  if (finalStatus === "checked_in") return history;

  history.push({ status: "in_progress", changed_at: appointmentStart.toISOString() });
  if (finalStatus === "in_progress") return history;

  history.push({ status: "completed", changed_at: appointmentEnd.toISOString() });
  return history;
}

function findStatusTimestamp(
  history: AppointmentStatusHistoryEntry[],
  status: AppointmentStatus,
): string | null {
  return history.find((entry) => entry.status === status)?.changed_at ?? null;
}

interface AppointmentSeed {
  patient_id: string;
  patient_name: string;
  patient_number: string;
  doctor_id: string;
  doctor_name: string;
  department: string;
  dayOffset: number;
  start_time: string;
  appointment_type: AppointmentType;
  status: AppointmentStatus;
  reason_for_visit: string;
}

const SEED: AppointmentSeed[] = [
  {
    patient_id: "pat-0001",
    patient_name: "Michael Chen",
    patient_number: "PAT-100001",
    doctor_id: "doc-0001",
    doctor_name: "Dr. Amara Okafor",
    department: "General Medicine",
    dayOffset: 0,
    start_time: "09:00",
    appointment_type: "consultation",
    status: "completed",
    reason_for_visit: "Routine annual checkup",
  },
  {
    patient_id: "pat-0002",
    patient_name: "Sarah Johnson",
    patient_number: "PAT-100002",
    doctor_id: "doc-0001",
    doctor_name: "Dr. Amara Okafor",
    department: "General Medicine",
    dayOffset: 0,
    start_time: "09:30",
    appointment_type: "follow_up",
    status: "completed",
    reason_for_visit: "Post-treatment follow-up",
  },
  {
    patient_id: "pat-0003",
    patient_name: "Amara Nwosu",
    patient_number: "PAT-100003",
    doctor_id: "doc-0001",
    doctor_name: "Dr. Amara Okafor",
    department: "General Medicine",
    dayOffset: -2,
    start_time: "14:00",
    appointment_type: "follow_up",
    status: "completed",
    reason_for_visit: "Diabetes management review",
  },
  {
    patient_id: "pat-0004",
    patient_name: "David Kim",
    patient_number: "PAT-100004",
    doctor_id: "doc-0002",
    doctor_name: "Dr. Daniel Reyes",
    department: "Cardiology",
    dayOffset: -1,
    start_time: "10:00",
    appointment_type: "consultation",
    status: "completed",
    reason_for_visit: "Chest pain evaluation",
  },
  {
    patient_id: "pat-0005",
    patient_name: "Priya Patel",
    patient_number: "PAT-100005",
    doctor_id: "doc-0003",
    doctor_name: "Dr. Priya Sharma",
    department: "Pediatrics",
    dayOffset: -1,
    start_time: "11:00",
    appointment_type: "consultation",
    status: "no_show",
    reason_for_visit: "Well-child visit",
  },
  {
    patient_id: "pat-0006",
    patient_name: "James Williams",
    patient_number: "PAT-100006",
    doctor_id: "doc-0004",
    doctor_name: "Dr. Marcus Webb",
    department: "Orthopedics",
    dayOffset: -3,
    start_time: "13:00",
    appointment_type: "procedure",
    status: "completed",
    reason_for_visit: "Knee injection",
  },
  {
    patient_id: "pat-0007",
    patient_name: "Olivia Martinez",
    patient_number: "PAT-100007",
    doctor_id: "doc-0005",
    doctor_name: "Dr. Hannah Kim",
    department: "Dermatology",
    dayOffset: -5,
    start_time: "15:00",
    appointment_type: "consultation",
    status: "cancelled",
    reason_for_visit: "Skin rash evaluation",
  },
  {
    patient_id: "pat-0008",
    patient_name: "Ethan Brown",
    patient_number: "PAT-100008",
    doctor_id: "doc-0001",
    doctor_name: "Dr. Amara Okafor",
    department: "General Medicine",
    dayOffset: 0,
    start_time: "10:30",
    appointment_type: "consultation",
    status: "in_progress",
    reason_for_visit: "Follow-up on hypertension medication",
  },
  {
    patient_id: "pat-0009",
    patient_name: "Grace Nguyen",
    patient_number: "PAT-100009",
    doctor_id: "doc-0006",
    doctor_name: "Dr. Elena Petrova",
    department: "Obstetrics & Gynecology",
    dayOffset: 0,
    start_time: "11:00",
    appointment_type: "consultation",
    status: "checked_in",
    reason_for_visit: "Prenatal checkup",
  },
  {
    patient_id: "pat-0010",
    patient_name: "Lucas Anderson",
    patient_number: "PAT-100010",
    doctor_id: "doc-0002",
    doctor_name: "Dr. Daniel Reyes",
    department: "Cardiology",
    dayOffset: 1,
    start_time: "09:00",
    appointment_type: "consultation",
    status: "confirmed",
    reason_for_visit: "Cardiac follow-up",
  },
  {
    patient_id: "pat-0011",
    patient_name: "Robert Lee",
    patient_number: "PAT-100011",
    doctor_id: "doc-0004",
    doctor_name: "Dr. Marcus Webb",
    department: "Orthopedics",
    dayOffset: 1,
    start_time: "10:00",
    appointment_type: "follow_up",
    status: "scheduled",
    reason_for_visit: "Post-surgical follow-up",
  },
  {
    patient_id: "pat-0012",
    patient_name: "Emma Garcia",
    patient_number: "PAT-100012",
    doctor_id: "doc-0008",
    doctor_name: "Dr. Grace Liu",
    department: "Behavioral Health",
    dayOffset: 2,
    start_time: "14:00",
    appointment_type: "consultation",
    status: "scheduled",
    reason_for_visit: "Anxiety management",
  },
  {
    patient_id: "pat-0013",
    patient_name: "Noah Thompson",
    patient_number: "PAT-100013",
    doctor_id: "doc-0001",
    doctor_name: "Dr. Amara Okafor",
    department: "General Medicine",
    dayOffset: 2,
    start_time: "09:00",
    appointment_type: "telemedicine",
    status: "confirmed",
    reason_for_visit: "Medication review",
  },
  {
    patient_id: "pat-0014",
    patient_name: "Ava Rodriguez",
    patient_number: "PAT-100014",
    doctor_id: "doc-0003",
    doctor_name: "Dr. Priya Sharma",
    department: "Pediatrics",
    dayOffset: 3,
    start_time: "15:30",
    appointment_type: "consultation",
    status: "scheduled",
    reason_for_visit: "Annual physical",
  },
  {
    patient_id: "pat-0015",
    patient_name: "William Davis",
    patient_number: "PAT-100015",
    doctor_id: "doc-0002",
    doctor_name: "Dr. Daniel Reyes",
    department: "Cardiology",
    dayOffset: 3,
    start_time: "11:00",
    appointment_type: "follow_up",
    status: "scheduled",
    reason_for_visit: "Blood pressure recheck",
  },
  {
    patient_id: "pat-0016",
    patient_name: "Sofia Torres",
    patient_number: "PAT-100016",
    doctor_id: "doc-0005",
    doctor_name: "Dr. Hannah Kim",
    department: "Dermatology",
    dayOffset: 4,
    start_time: "13:30",
    appointment_type: "consultation",
    status: "scheduled",
    reason_for_visit: "Mole check",
  },
  {
    patient_id: "pat-0017",
    patient_name: "Benjamin White",
    patient_number: "PAT-100017",
    doctor_id: "doc-0004",
    doctor_name: "Dr. Marcus Webb",
    department: "Orthopedics",
    dayOffset: 5,
    start_time: "10:00",
    appointment_type: "emergency",
    status: "scheduled",
    reason_for_visit: "Acute back pain",
  },
  {
    patient_id: "pat-0018",
    patient_name: "Isabella Clark",
    patient_number: "PAT-100018",
    doctor_id: "doc-0006",
    doctor_name: "Dr. Elena Petrova",
    department: "Obstetrics & Gynecology",
    dayOffset: 5,
    start_time: "09:30",
    appointment_type: "consultation",
    status: "scheduled",
    reason_for_visit: "Well visit",
  },
  {
    patient_id: "pat-0001",
    patient_name: "Michael Chen",
    patient_number: "PAT-100001",
    doctor_id: "doc-0002",
    doctor_name: "Dr. Daniel Reyes",
    department: "Cardiology",
    dayOffset: 7,
    start_time: "09:00",
    appointment_type: "telemedicine",
    status: "scheduled",
    reason_for_visit: "Cardiology consult",
  },
  {
    patient_id: "pat-0003",
    patient_name: "Amara Nwosu",
    patient_number: "PAT-100003",
    doctor_id: "doc-0001",
    doctor_name: "Dr. Amara Okafor",
    department: "General Medicine",
    dayOffset: 10,
    start_time: "14:00",
    appointment_type: "follow_up",
    status: "scheduled",
    reason_for_visit: "Diabetes follow-up",
  },
];

let appointments: AppointmentDetail[] = SEED.map((seed, index) => {
  const num = index + 1;
  const appointment_date = dateOffset(seed.dayOffset);
  const end_time = computeEndTime(seed.start_time);
  const appointmentStart = combineDateTime(appointment_date, seed.start_time);
  const appointmentEnd = combineDateTime(appointment_date, end_time);
  const createdAt = new Date(appointmentStart.getTime() - (3 + (num % 5)) * 24 * 60 * 60_000);
  const status_history = buildStatusHistory(
    seed.status,
    createdAt,
    appointmentStart,
    appointmentEnd,
  );

  return {
    appointment_id: `apt-${String(num).padStart(4, "0")}`,
    organization_id: ORG_ID,
    appointment_number: `APT-${90000 + num}`,
    patient_id: seed.patient_id,
    patient_name: seed.patient_name,
    patient_number: seed.patient_number,
    doctor_id: seed.doctor_id,
    doctor_name: seed.doctor_name,
    department: seed.department,
    appointment_date,
    start_time: seed.start_time,
    end_time,
    appointment_type: seed.appointment_type,
    status: seed.status,
    reason_for_visit: seed.reason_for_visit,
    created_at: createdAt.toISOString(),
    notes: seed.status === "completed" ? "Visit completed without complications." : null,
    booked_by_name: "Front Desk",
    checked_in_at: findStatusTimestamp(status_history, "checked_in"),
    completed_at: findStatusTimestamp(status_history, "completed"),
    cancelled_at: findStatusTimestamp(status_history, "cancelled"),
    status_history,
  };
});

// --- Repository: reads -----------------------------------------------

export interface AppointmentListParams {
  search?: string;
  status?: AppointmentStatus | "all";
  appointmentType?: AppointmentType | "all";
  date?: string;
  sortBy?: "appointment_date" | "patient_name" | "doctor_name" | "status";
  sortDirection?: "asc" | "desc";
  page?: number;
  pageSize?: number;
}

function matchesSearch(appointment: Appointment, search: string): boolean {
  const needle = search.trim().toLowerCase();
  if (!needle) return true;
  return (
    appointment.appointment_number.toLowerCase().includes(needle) ||
    appointment.patient_name.toLowerCase().includes(needle) ||
    appointment.doctor_name.toLowerCase().includes(needle) ||
    (appointment.reason_for_visit ?? "").toLowerCase().includes(needle)
  );
}

function sortKey(
  appointment: Appointment,
  sortBy: NonNullable<AppointmentListParams["sortBy"]>,
): string {
  if (sortBy === "appointment_date")
    return `${appointment.appointment_date} ${appointment.start_time}`;
  return String(appointment[sortBy]);
}

function stripDetail(appointment: AppointmentDetail): Appointment {
  return {
    appointment_id: appointment.appointment_id,
    organization_id: appointment.organization_id,
    appointment_number: appointment.appointment_number,
    patient_id: appointment.patient_id,
    patient_name: appointment.patient_name,
    patient_number: appointment.patient_number,
    doctor_id: appointment.doctor_id,
    doctor_name: appointment.doctor_name,
    department: appointment.department,
    appointment_date: appointment.appointment_date,
    start_time: appointment.start_time,
    end_time: appointment.end_time,
    appointment_type: appointment.appointment_type,
    status: appointment.status,
    reason_for_visit: appointment.reason_for_visit,
    created_at: appointment.created_at,
  };
}

export function listAppointments(
  params: AppointmentListParams = {},
): Promise<PaginatedResponse<Appointment>> {
  const {
    search = "",
    status = "all",
    appointmentType = "all",
    date,
    sortBy = "appointment_date",
    sortDirection = "asc",
    page = 1,
    pageSize = 10,
  } = params;

  let filtered = appointments.filter((appointment) => matchesSearch(appointment, search));
  if (status !== "all") {
    filtered = filtered.filter((appointment) => appointment.status === status);
  }
  if (appointmentType !== "all") {
    filtered = filtered.filter((appointment) => appointment.appointment_type === appointmentType);
  }
  if (date) {
    filtered = filtered.filter((appointment) => appointment.appointment_date === date);
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

export function getAppointment(appointmentId: string): Promise<AppointmentDetail | null> {
  const found =
    appointments.find((appointment) => appointment.appointment_id === appointmentId) ?? null;
  return mockFetch(found, 300);
}

// --- Repository: writes -------------------------------------------------

export interface AppointmentFormInput {
  patient_id: string;
  doctor_id: string;
  appointment_date: string;
  start_time: string;
  end_time: string;
  appointment_type: AppointmentType;
  reason_for_visit: string;
  notes: string;
}

// Mock stand-ins for the denormalized display fields a real create/update
// call wouldn't need the caller to supply (the backend would resolve
// `patient_id`/`doctor_id` server-side). Looked up from the same seed
// directory rows already in memory so newly created appointments still
// show a real name instead of "Unknown".
function resolvePatientDisplay(patientId: string): { name: string; number: string } {
  const existing = appointments.find((appointment) => appointment.patient_id === patientId);
  return existing
    ? { name: existing.patient_name, number: existing.patient_number }
    : { name: "Unknown Patient", number: "—" };
}

function resolveDoctorDisplay(doctorId: string): { name: string; department: string } {
  const existing = appointments.find((appointment) => appointment.doctor_id === doctorId);
  return existing
    ? { name: existing.doctor_name, department: existing.department }
    : { name: "Unknown Doctor", department: "—" };
}

export async function createAppointment(input: AppointmentFormInput): Promise<AppointmentDetail> {
  const id = generateId("apt");
  const nextNumber = 90000 + appointments.length + 1;
  const patient = resolvePatientDisplay(input.patient_id);
  const doctor = resolveDoctorDisplay(input.doctor_id);
  const now = new Date();
  const status_history: AppointmentStatusHistoryEntry[] = [
    { status: "scheduled", changed_at: now.toISOString() },
  ];

  const created: AppointmentDetail = {
    appointment_id: id,
    organization_id: ORG_ID,
    appointment_number: `APT-${nextNumber}`,
    patient_id: input.patient_id,
    patient_name: patient.name,
    patient_number: patient.number,
    doctor_id: input.doctor_id,
    doctor_name: doctor.name,
    department: doctor.department,
    appointment_date: input.appointment_date,
    start_time: input.start_time,
    end_time: input.end_time,
    appointment_type: input.appointment_type,
    status: "scheduled",
    reason_for_visit: input.reason_for_visit || null,
    created_at: now.toISOString(),
    notes: input.notes || null,
    booked_by_name: "Front Desk",
    checked_in_at: null,
    completed_at: null,
    cancelled_at: null,
    status_history,
  };

  appointments = [created, ...appointments];
  return mockFetch(created, 500);
}

export async function updateAppointment(
  appointmentId: string,
  input: AppointmentFormInput,
): Promise<AppointmentDetail> {
  const index = appointments.findIndex(
    (appointment) => appointment.appointment_id === appointmentId,
  );
  const existing = appointments[index];
  if (!existing) {
    throw new Error(`Appointment ${appointmentId} not found`);
  }

  const patient =
    input.patient_id === existing.patient_id
      ? { name: existing.patient_name, number: existing.patient_number }
      : resolvePatientDisplay(input.patient_id);
  const doctor =
    input.doctor_id === existing.doctor_id
      ? { name: existing.doctor_name, department: existing.department }
      : resolveDoctorDisplay(input.doctor_id);

  const updated: AppointmentDetail = {
    ...existing,
    patient_id: input.patient_id,
    patient_name: patient.name,
    patient_number: patient.number,
    doctor_id: input.doctor_id,
    doctor_name: doctor.name,
    department: doctor.department,
    appointment_date: input.appointment_date,
    start_time: input.start_time,
    end_time: input.end_time,
    appointment_type: input.appointment_type,
    reason_for_visit: input.reason_for_visit || null,
    notes: input.notes || null,
  };

  appointments = [...appointments.slice(0, index), updated, ...appointments.slice(index + 1)];
  return mockFetch(updated, 500);
}

export async function changeAppointmentStatus(
  appointmentId: string,
  nextStatus: AppointmentStatus,
  note?: string,
): Promise<AppointmentDetail> {
  const index = appointments.findIndex(
    (appointment) => appointment.appointment_id === appointmentId,
  );
  const existing = appointments[index];
  if (!existing) {
    throw new Error(`Appointment ${appointmentId} not found`);
  }
  if (!getAllowedTransitions(existing.status).includes(nextStatus)) {
    throw new Error(`Cannot transition appointment from ${existing.status} to ${nextStatus}`);
  }

  const changed_at = new Date().toISOString();
  const status_history = [...existing.status_history, { status: nextStatus, changed_at, note }];

  const updated: AppointmentDetail = {
    ...existing,
    status: nextStatus,
    status_history,
    checked_in_at: nextStatus === "checked_in" ? changed_at : existing.checked_in_at,
    completed_at: nextStatus === "completed" ? changed_at : existing.completed_at,
    cancelled_at: nextStatus === "cancelled" ? changed_at : existing.cancelled_at,
  };

  appointments = [...appointments.slice(0, index), updated, ...appointments.slice(index + 1)];
  return mockFetch(updated, 400);
}

export function appointmentToFormInput(appointment: AppointmentDetail): AppointmentFormInput {
  return {
    patient_id: appointment.patient_id,
    doctor_id: appointment.doctor_id,
    appointment_date: appointment.appointment_date,
    start_time: appointment.start_time,
    end_time: appointment.end_time,
    appointment_type: appointment.appointment_type,
    reason_for_visit: appointment.reason_for_visit ?? "",
    notes: appointment.notes ?? "",
  };
}
