import { Bell, CalendarCheck, CalendarClock, ClipboardList, UserCheck } from "lucide-react";

import { StatCard } from "@/components/shared/charts/stat-card";
import { CardSkeleton } from "@/components/shared/states/card-skeleton";
import type { DoctorDashboardStats } from "@/lib/mock/doctor-dashboard";

interface StatsGridProps {
  stats?: DoctorDashboardStats;
  isLoading?: boolean;
}

// The icon/label-per-field mapping is presentation, not data — the
// underlying numbers always come from the caller via `stats`, never
// hardcoded here.
export function StatsGrid({ stats, isLoading }: StatsGridProps) {
  if (isLoading || !stats) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {Array.from({ length: 5 }).map((_, index) => (
          <CardSkeleton key={index} />
        ))}
      </div>
    );
  }

  const items = [
    {
      key: "appointments",
      label: "Today's Appointments",
      value: stats.todays_appointments,
      icon: CalendarClock,
    },
    {
      key: "seen",
      label: "Patients Seen Today",
      value: stats.patients_seen_today,
      icon: UserCheck,
    },
    {
      key: "notes",
      label: "Pending Clinical Notes",
      value: stats.pending_clinical_notes,
      icon: ClipboardList,
    },
    {
      key: "notifications",
      label: "Unread Notifications",
      value: stats.unread_notifications,
      icon: Bell,
    },
    {
      key: "followups",
      label: "Upcoming Follow-ups",
      value: stats.upcoming_follow_ups,
      icon: CalendarCheck,
    },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      {items.map((item) => (
        <StatCard key={item.key} label={item.label} value={item.value} icon={item.icon} />
      ))}
    </div>
  );
}
