import { Badge } from "@/components/ui/badge";
import type { PatientStatus } from "@/lib/mock/patients";

const STATUS_LABEL: Record<PatientStatus, string> = {
  active: "Active",
  inactive: "Inactive",
};

const STATUS_VARIANT: Record<PatientStatus, "default" | "secondary"> = {
  active: "default",
  inactive: "secondary",
};

export function PatientStatusBadge({ status }: { status: PatientStatus }) {
  return <Badge variant={STATUS_VARIANT[status]}>{STATUS_LABEL[status]}</Badge>;
}
