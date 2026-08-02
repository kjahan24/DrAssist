import { Badge } from "@/components/ui/badge";
import type { ClinicalNoteStatus } from "@/lib/mock/clinical-notes";

const STATUS_LABEL: Record<ClinicalNoteStatus, string> = {
  draft: "Draft",
  in_review: "In Review",
  signed: "Signed",
  locked: "Locked",
};

const STATUS_VARIANT: Record<
  ClinicalNoteStatus,
  "default" | "secondary" | "destructive" | "outline"
> = {
  draft: "outline",
  in_review: "secondary",
  signed: "default",
  locked: "secondary",
};

export function ClinicalNoteStatusBadge({ status }: { status: ClinicalNoteStatus }) {
  return <Badge variant={STATUS_VARIANT[status]}>{STATUS_LABEL[status]}</Badge>;
}
