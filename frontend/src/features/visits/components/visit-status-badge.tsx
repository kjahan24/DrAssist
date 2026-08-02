import { Badge } from "@/components/ui/badge";
import type { VisitStatus } from "@/lib/mock/visits";

const STATUS_LABEL: Record<VisitStatus, string> = {
  scheduled: "Scheduled",
  checked_in: "Checked In",
  in_progress: "In Progress",
  completed: "Completed",
  cancelled: "Cancelled",
  no_show: "No Show",
};

const STATUS_VARIANT: Record<VisitStatus, "default" | "secondary" | "destructive" | "outline"> = {
  scheduled: "outline",
  checked_in: "secondary",
  in_progress: "default",
  completed: "secondary",
  cancelled: "destructive",
  no_show: "destructive",
};

export function VisitStatusBadge({ status }: { status: VisitStatus }) {
  return <Badge variant={STATUS_VARIANT[status]}>{STATUS_LABEL[status]}</Badge>;
}
