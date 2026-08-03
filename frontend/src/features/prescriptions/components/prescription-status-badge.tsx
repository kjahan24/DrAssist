import { Badge } from "@/components/ui/badge";
import type { PrescriptionStatus } from "@/lib/mock/prescriptions";

const STATUS_LABEL: Record<PrescriptionStatus, string> = {
  draft: "Draft",
  final: "Final",
};

const STATUS_VARIANT: Record<PrescriptionStatus, "default" | "outline"> = {
  draft: "outline",
  final: "default",
};

export function PrescriptionStatusBadge({ status }: { status: PrescriptionStatus }) {
  return <Badge variant={STATUS_VARIANT[status]}>{STATUS_LABEL[status]}</Badge>;
}
