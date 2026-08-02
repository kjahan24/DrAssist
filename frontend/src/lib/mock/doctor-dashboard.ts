// Temporary frontend mock service for the Doctor Dashboard
// (`app/(dashboard)/dashboard/page.tsx`). Every export below is meant to
// be deleted wholesale once the real backend endpoints exist — that's
// why every "fetch" function is `async` and returns a `Promise` exactly
// like a real `httpClient` call would: swapping a mock for the real
// thing later means changing a `queryFn` in
// `features/dashboard/hooks/use-doctor-dashboard.ts` from
// `fetchXxx` (this file) to `() => httpClient.get(...)` — nothing else
// in the component tree changes. Field names are chosen to plausibly
// match the real backend modules they'll eventually come from
// (Appointment, Patient, SOAP Notes, Lab Orders, Prescriptions,
// Documents, Notifications) so that mapping is as close to a no-op as
// realistically possible ahead of time.
//
// No component in `features/dashboard/components/` imports this file
// directly — only the hooks in `use-doctor-dashboard.ts` do, keeping the
// "no mock business logic inside reusable components" boundary real: a
// component only ever sees typed props, never knows data is mocked.

const MIN_LATENCY_MS = 300;

function mockFetch<T>(value: T, latencyMs: number = MIN_LATENCY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), latencyMs));
}

// --- Doctor profile -----------------------------------------------------
// The real `AuthenticatedPrincipal` (`types/index.ts`) only carries
// identity + permissions, not a display name or organization name — see
// that type's own docstring. Until a real "who am I" / organization
// lookup endpoint exists, this is the one place those two display values
// come from.

export interface DoctorProfile {
  display_name: string;
  organization_name: string;
}

export function fetchDoctorProfile(): Promise<DoctorProfile> {
  return mockFetch(
    {
      display_name: "Dr. Amara Okafor",
      organization_name: "Riverside Family Health Clinic",
    },
    250,
  );
}

// --- KPI stats ------------------------------------------------------------

export interface DoctorDashboardStats {
  todays_appointments: number;
  patients_seen_today: number;
  pending_clinical_notes: number;
  unread_notifications: number;
  upcoming_follow_ups: number;
}

export function fetchDoctorDashboardStats(): Promise<DoctorDashboardStats> {
  return mockFetch(
    {
      todays_appointments: 9,
      patients_seen_today: 4,
      pending_clinical_notes: 3,
      unread_notifications: 5,
      upcoming_follow_ups: 6,
    },
    450,
  );
}

// --- Today's schedule -------------------------------------------------

export type AppointmentStatus =
  "scheduled" | "confirmed" | "checked_in" | "in_progress" | "completed" | "cancelled" | "no_show";

export interface ScheduleAppointment {
  appointment_id: string;
  scheduled_time: string; // ISO 8601
  patient_name: string;
  visit_type: string;
  status: AppointmentStatus;
}

function todayAt(hour: number, minute: number): string {
  const date = new Date();
  date.setHours(hour, minute, 0, 0);
  return date.toISOString();
}

export function fetchTodaysSchedule(): Promise<ScheduleAppointment[]> {
  return mockFetch(
    [
      {
        appointment_id: "apt-1001",
        scheduled_time: todayAt(8, 30),
        patient_name: "Michael Chen",
        visit_type: "Annual Physical",
        status: "completed",
      },
      {
        appointment_id: "apt-1002",
        scheduled_time: todayAt(9, 15),
        patient_name: "Sarah Johnson",
        visit_type: "Follow-up",
        status: "completed",
      },
      {
        appointment_id: "apt-1003",
        scheduled_time: todayAt(10, 0),
        patient_name: "David Kim",
        visit_type: "New Patient Consultation",
        status: "in_progress",
      },
      {
        appointment_id: "apt-1004",
        scheduled_time: todayAt(10, 45),
        patient_name: "Priya Patel",
        visit_type: "Telehealth",
        status: "confirmed",
      },
      {
        appointment_id: "apt-1005",
        scheduled_time: todayAt(11, 30),
        patient_name: "James Williams",
        visit_type: "Follow-up",
        status: "checked_in",
      },
      {
        appointment_id: "apt-1006",
        scheduled_time: todayAt(13, 0),
        patient_name: "Olivia Martinez",
        visit_type: "Urgent Care",
        status: "scheduled",
      },
      {
        appointment_id: "apt-1007",
        scheduled_time: todayAt(14, 15),
        patient_name: "Ethan Brown",
        visit_type: "Annual Physical",
        status: "scheduled",
      },
      {
        appointment_id: "apt-1008",
        scheduled_time: todayAt(15, 30),
        patient_name: "Grace Nguyen",
        visit_type: "Follow-up",
        status: "cancelled",
      },
      {
        appointment_id: "apt-1009",
        scheduled_time: todayAt(16, 15),
        patient_name: "Lucas Anderson",
        visit_type: "Telehealth",
        status: "no_show",
      },
    ],
    600,
  );
}

// --- Recent patients --------------------------------------------------

export interface RecentPatient {
  patient_id: string;
  full_name: string;
  age: number;
  gender: "male" | "female" | "other";
  last_visit_date: string; // ISO 8601 date
  avatar_initials: string;
}

export function fetchRecentPatients(): Promise<RecentPatient[]> {
  return mockFetch(
    [
      {
        patient_id: "pat-2001",
        full_name: "Michael Chen",
        age: 47,
        gender: "male",
        last_visit_date: new Date().toISOString(),
        avatar_initials: "MC",
      },
      {
        patient_id: "pat-2002",
        full_name: "Sarah Johnson",
        age: 34,
        gender: "female",
        last_visit_date: new Date().toISOString(),
        avatar_initials: "SJ",
      },
      {
        patient_id: "pat-2003",
        full_name: "Amara Nwosu",
        age: 62,
        gender: "female",
        last_visit_date: new Date(Date.now() - 2 * 86_400_000).toISOString(),
        avatar_initials: "AN",
      },
      {
        patient_id: "pat-2004",
        full_name: "Robert Lee",
        age: 55,
        gender: "male",
        last_visit_date: new Date(Date.now() - 4 * 86_400_000).toISOString(),
        avatar_initials: "RL",
      },
      {
        patient_id: "pat-2005",
        full_name: "Priya Patel",
        age: 29,
        gender: "female",
        last_visit_date: new Date(Date.now() - 6 * 86_400_000).toISOString(),
        avatar_initials: "PP",
      },
    ],
    650,
  );
}

// --- Pending tasks ------------------------------------------------------

export type PendingTaskType =
  "soap_note" | "lab_review" | "prescription_signature" | "document_review";

export interface PendingTask {
  task_id: string;
  type: PendingTaskType;
  title: string;
  patient_name: string;
  due_date: string; // ISO 8601
  priority: "low" | "medium" | "high";
}

export function fetchPendingTasks(): Promise<PendingTask[]> {
  return mockFetch(
    [
      {
        task_id: "task-3001",
        type: "soap_note",
        title: "Complete SOAP note",
        patient_name: "David Kim",
        due_date: new Date().toISOString(),
        priority: "high",
      },
      {
        task_id: "task-3002",
        type: "lab_review",
        title: "Review lab report",
        patient_name: "Robert Lee",
        due_date: new Date().toISOString(),
        priority: "high",
      },
      {
        task_id: "task-3003",
        type: "prescription_signature",
        title: "Sign prescription",
        patient_name: "Priya Patel",
        due_date: new Date(Date.now() + 86_400_000).toISOString(),
        priority: "medium",
      },
      {
        task_id: "task-3004",
        type: "document_review",
        title: "Review uploaded documents",
        patient_name: "Amara Nwosu",
        due_date: new Date(Date.now() + 86_400_000).toISOString(),
        priority: "low",
      },
    ],
    550,
  );
}

// --- Recent clinical activity -------------------------------------------

export type ActivityType =
  "appointment_completed" | "soap_note_saved" | "document_uploaded" | "patient_registered";

export interface ActivityItem {
  activity_id: string;
  type: ActivityType;
  description: string;
  timestamp: string; // ISO 8601
}

export function fetchRecentActivity(): Promise<ActivityItem[]> {
  return mockFetch(
    [
      {
        activity_id: "act-4001",
        type: "appointment_completed",
        description: "Appointment completed with Sarah Johnson",
        timestamp: new Date(Date.now() - 20 * 60_000).toISOString(),
      },
      {
        activity_id: "act-4002",
        type: "soap_note_saved",
        description: "SOAP note saved for Michael Chen",
        timestamp: new Date(Date.now() - 45 * 60_000).toISOString(),
      },
      {
        activity_id: "act-4003",
        type: "document_uploaded",
        description: "Lab results uploaded for Robert Lee",
        timestamp: new Date(Date.now() - 2 * 3_600_000).toISOString(),
      },
      {
        activity_id: "act-4004",
        type: "patient_registered",
        description: "New patient Grace Nguyen registered",
        timestamp: new Date(Date.now() - 5 * 3_600_000).toISOString(),
      },
      {
        activity_id: "act-4005",
        type: "appointment_completed",
        description: "Appointment completed with Ethan Brown",
        timestamp: new Date(Date.now() - 26 * 3_600_000).toISOString(),
      },
    ],
    700,
  );
}

// --- Notifications --------------------------------------------------------

export type NotificationType =
  "lab_result" | "appointment_reminder" | "document_uploaded" | "system";

export interface DashboardNotification {
  notification_id: string;
  type: NotificationType;
  title: string;
  message: string;
  timestamp: string; // ISO 8601
  read: boolean;
}

export function fetchDashboardNotifications(): Promise<DashboardNotification[]> {
  return mockFetch(
    [
      {
        notification_id: "notif-5001",
        type: "lab_result",
        title: "Lab result available",
        message: "Robert Lee's blood panel results are ready to review.",
        timestamp: new Date(Date.now() - 15 * 60_000).toISOString(),
        read: false,
      },
      {
        notification_id: "notif-5002",
        type: "appointment_reminder",
        title: "Appointment starting soon",
        message: "David Kim's consultation starts in 10 minutes.",
        timestamp: new Date(Date.now() - 30 * 60_000).toISOString(),
        read: false,
      },
      {
        notification_id: "notif-5003",
        type: "document_uploaded",
        title: "Patient uploaded a document",
        message: "Amara Nwosu uploaded an insurance card.",
        timestamp: new Date(Date.now() - 3 * 3_600_000).toISOString(),
        read: false,
      },
      {
        notification_id: "notif-5004",
        type: "system",
        title: "Scheduled maintenance",
        message: "A brief maintenance window is planned for this weekend.",
        timestamp: new Date(Date.now() - 26 * 3_600_000).toISOString(),
        read: true,
      },
    ],
    400,
  );
}

// --- Upcoming (calendar preview) ----------------------------------------
// Deliberately a lighter shape than `ScheduleAppointment` — this is a
// glance-ahead preview, not the full calendar this module explicitly
// excludes.

export interface UpcomingCalendarItem {
  date: string; // ISO 8601 date
  time: string;
  patient_name: string;
  visit_type: string;
}

export function fetchUpcomingCalendar(): Promise<UpcomingCalendarItem[]> {
  const addDays = (days: number) => new Date(Date.now() + days * 86_400_000).toISOString();

  return mockFetch(
    [
      { date: addDays(1), time: "9:00 AM", patient_name: "Grace Nguyen", visit_type: "Follow-up" },
      {
        date: addDays(1),
        time: "11:30 AM",
        patient_name: "Lucas Anderson",
        visit_type: "Telehealth",
      },
      {
        date: addDays(2),
        time: "10:00 AM",
        patient_name: "James Williams",
        visit_type: "Annual Physical",
      },
    ],
    600,
  );
}

// --- Quick action links ---------------------------------------------------
// Static navigation configuration, not "dashboard data" in the KPI/list
// sense — kept here anyway so every piece of this page's content has one
// discoverable home.

export interface QuickActionLink {
  title: string;
  description: string;
  href: string;
}

export const doctorDashboardQuickActions: QuickActionLink[] = [
  {
    title: "New Appointment",
    description: "Schedule a new visit.",
    href: "/dashboard/appointments/new",
  },
  { title: "New Patient", description: "Register a new patient.", href: "/dashboard/patients/new" },
  { title: "Open Calendar", description: "View your full schedule.", href: "/dashboard/schedule" },
  {
    title: "Clinical Notes",
    description: "Review and document visits.",
    href: "/dashboard/clinical-notes",
  },
  {
    title: "Medical Documents",
    description: "Access patient files.",
    href: "/dashboard/documents",
  },
  { title: "Timeline", description: "View patient history.", href: "/dashboard/timeline" },
];
