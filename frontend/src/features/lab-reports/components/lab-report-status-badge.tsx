import { Badge } from "@/components/ui/badge";
import type { LabReportStatus } from "@/lib/mock/lab-reports";

const STATUS_LABEL: Record<LabReportStatus, string> = {
  draft: "Draft",
  ordered: "Ordered",
  collected: "Collected",
  final: "Final",
  cancelled: "Cancelled",
};

const STATUS_VARIANT: Record<LabReportStatus, "default" | "secondary" | "destructive" | "outline"> =
  {
    draft: "outline",
    ordered: "secondary",
    collected: "secondary",
    final: "default",
    cancelled: "destructive",
  };

export function LabReportStatusBadge({ status }: { status: LabReportStatus }) {
  return <Badge variant={STATUS_VARIANT[status]}>{STATUS_LABEL[status]}</Badge>;
}
