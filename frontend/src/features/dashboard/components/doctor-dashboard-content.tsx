"use client";

import { ActivityTimeline } from "@/features/dashboard/components/activity-timeline";
import { CalendarPreview } from "@/features/dashboard/components/calendar-preview";
import { DoctorDashboardHeader } from "@/features/dashboard/components/doctor-dashboard-header";
import { NotificationPanel } from "@/features/dashboard/components/notification-panel";
import { PatientList } from "@/features/dashboard/components/patient-list";
import { PendingTasks } from "@/features/dashboard/components/pending-tasks";
import { QuickActions } from "@/features/dashboard/components/quick-actions";
import { StatsGrid } from "@/features/dashboard/components/stats-grid";
import { TodaySchedule } from "@/features/dashboard/components/today-schedule";
import {
  useDashboardNotifications,
  useDoctorDashboardStats,
  useDoctorProfile,
  usePendingTasks,
  useRecentActivity,
  useRecentPatients,
  useTodaysSchedule,
  useUpcomingCalendar,
} from "@/features/dashboard/hooks/use-doctor-dashboard";

// Each section fires its own query and resolves independently — the same
// shape a real page calling several distinct backend endpoints in
// parallel would have, so nothing about this composition needs to change
// when `lib/mock/doctor-dashboard.ts` is eventually replaced.
export function DoctorDashboardContent() {
  const profileQuery = useDoctorProfile();
  const statsQuery = useDoctorDashboardStats();
  const scheduleQuery = useTodaysSchedule();
  const patientsQuery = useRecentPatients();
  const tasksQuery = usePendingTasks();
  const activityQuery = useRecentActivity();
  const notificationsQuery = useDashboardNotifications();
  const calendarQuery = useUpcomingCalendar();

  return (
    <div className="space-y-6">
      <DoctorDashboardHeader
        doctorName={profileQuery.data?.display_name}
        organizationName={profileQuery.data?.organization_name}
        isLoading={profileQuery.isLoading}
      />

      <StatsGrid stats={statsQuery.data} isLoading={statsQuery.isLoading} />

      <QuickActions />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <TodaySchedule
            appointments={scheduleQuery.data ?? []}
            isLoading={scheduleQuery.isLoading}
          />
          <PatientList patients={patientsQuery.data ?? []} isLoading={patientsQuery.isLoading} />
          <ActivityTimeline items={activityQuery.data ?? []} isLoading={activityQuery.isLoading} />
        </div>
        <div className="space-y-6">
          <PendingTasks tasks={tasksQuery.data ?? []} isLoading={tasksQuery.isLoading} />
          <NotificationPanel
            notifications={notificationsQuery.data ?? []}
            isLoading={notificationsQuery.isLoading}
          />
          <CalendarPreview items={calendarQuery.data ?? []} isLoading={calendarQuery.isLoading} />
        </div>
      </div>
    </div>
  );
}
