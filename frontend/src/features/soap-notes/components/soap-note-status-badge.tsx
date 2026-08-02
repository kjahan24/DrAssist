import { Badge } from "@/components/ui/badge";
import type { SOAPNoteStatus } from "@/lib/mock/soap-notes";

const STATUS_LABEL: Record<SOAPNoteStatus, string> = {
  draft: "Draft",
  final: "Final",
};

const STATUS_VARIANT: Record<SOAPNoteStatus, "default" | "outline"> = {
  draft: "outline",
  final: "default",
};

export function SoapNoteStatusBadge({ status }: { status: SOAPNoteStatus }) {
  return <Badge variant={STATUS_VARIANT[status]}>{STATUS_LABEL[status]}</Badge>;
}
