import { Badge } from "@/components/ui/badge";
import { getDocumentStatusLabel, type DocumentStatus } from "@/lib/mock/documents";

const STATUS_VARIANT: Record<DocumentStatus, "default" | "outline" | "secondary" | "destructive"> =
  {
    uploading: "outline",
    active: "default",
    archived: "secondary",
    deleted: "destructive",
  };

export function DocumentStatusBadge({ status }: { status: DocumentStatus }) {
  return <Badge variant={STATUS_VARIANT[status]}>{getDocumentStatusLabel(status)}</Badge>;
}
