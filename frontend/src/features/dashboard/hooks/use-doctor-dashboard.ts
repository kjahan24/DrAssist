"use client";

import { useQuery } from "@tanstack/react-query";

import { createQueryKeys } from "@/lib/query-keys";
import {
  fetchDashboardNotifications,
  fetchDoctorDashboardStats,
  fetchDoctorProfile,
  fetchPendingTasks,
  fetchRecentActivity,
  fetchRecentPatients,
  fetchTodaysSchedule,
  fetchUpcomingCalendar,
} from "@/lib/mock/doctor-dashboard";

// One query-key namespace for the whole page, built on the same
// `createQueryKeys` factory every feature module is expected to use
// (`lib/query-keys.ts`). Swapping mock data for real backend calls later
// means changing only the `queryFn` line in each hook below — the key,
// the loading/error contract, and every consumer stay identical.
const doctorDashboardKeys = createQueryKeys("doctor-dashboard");

export function useDoctorProfile() {
  return useQuery({
    queryKey: [...doctorDashboardKeys.all, "profile"],
    queryFn: fetchDoctorProfile,
  });
}

export function useDoctorDashboardStats() {
  return useQuery({
    queryKey: [...doctorDashboardKeys.all, "stats"],
    queryFn: fetchDoctorDashboardStats,
  });
}

export function useTodaysSchedule() {
  return useQuery({
    queryKey: [...doctorDashboardKeys.all, "schedule"],
    queryFn: fetchTodaysSchedule,
  });
}

export function useRecentPatients() {
  return useQuery({
    queryKey: [...doctorDashboardKeys.all, "recent-patients"],
    queryFn: fetchRecentPatients,
  });
}

export function usePendingTasks() {
  return useQuery({
    queryKey: [...doctorDashboardKeys.all, "pending-tasks"],
    queryFn: fetchPendingTasks,
  });
}

export function useRecentActivity() {
  return useQuery({
    queryKey: [...doctorDashboardKeys.all, "recent-activity"],
    queryFn: fetchRecentActivity,
  });
}

export function useDashboardNotifications() {
  return useQuery({
    queryKey: [...doctorDashboardKeys.all, "notifications"],
    queryFn: fetchDashboardNotifications,
  });
}

export function useUpcomingCalendar() {
  return useQuery({
    queryKey: [...doctorDashboardKeys.all, "upcoming-calendar"],
    queryFn: fetchUpcomingCalendar,
  });
}
