import { Badge } from "@/components/ui/badge";
import type { AppointmentStatus } from "@/lib/mock/appointments";

const STATUS_LABEL: Record<AppointmentStatus, string> = {
  scheduled: "Scheduled",
  confirmed: "Confirmed",
  checked_in: "Checked In",
  in_progress: "In Progress",
  completed: "Completed",
  cancelled: "Cancelled",
  no_show: "No Show",
};

const STATUS_VARIANT: Record<
  AppointmentStatus,
  "default" | "secondary" | "destructive" | "outline"
> = {
  scheduled: "outline",
  confirmed: "secondary",
  checked_in: "secondary",
  in_progress: "default",
  completed: "secondary",
  cancelled: "destructive",
  no_show: "destructive",
};

export function AppointmentStatusBadge({ status }: { status: AppointmentStatus }) {
  return <Badge variant={STATUS_VARIANT[status]}>{STATUS_LABEL[status]}</Badge>;
}
