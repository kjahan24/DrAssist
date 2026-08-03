import Link from "next/link";
import { Download } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { DocumentPatientIdentity } from "@/features/documents/components/document-patient-identity";
import { DocumentPreview } from "@/features/documents/components/document-preview";
import { DocumentStatusBadge } from "@/features/documents/components/document-status-badge";
import { formatDate, formatFileSize } from "@/lib/format";
import {
  getDocumentCategoryLabel,
  isDocumentEditable,
  type MedicalDocument,
} from "@/lib/mock/documents";
import { showSimulatedDownloadToast } from "@/features/documents/lib/simulated-download";

// Reused in two places: the mobile stack below `DocumentTable` (List
// view, hidden `md:` and up) and as the item renderer for `DocumentGrid`
// (Grid view, visible at every breakpoint) — same reuse pattern as
// `PrescriptionCard`.
export function DocumentCard({ document }: { document: MedicalDocument }) {
  return (
    <Card>
      <CardContent className="space-y-3 pt-6">
        <div className="flex items-start justify-between gap-2">
          <div className="flex min-w-0 items-center gap-3">
            <DocumentPreview mimeType={document.mime_type} extension={document.extension} />
            <div className="min-w-0">
              <Link
                href={`/dashboard/documents/${document.document_id}`}
                className="truncate text-sm font-medium text-primary underline-offset-4 hover:underline"
              >
                {document.title}
              </Link>
              <p className="truncate text-xs text-muted-foreground">{document.document_number}</p>
            </div>
          </div>
          <DocumentStatusBadge status={document.status} />
        </div>

        <DocumentPatientIdentity document={document} />

        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <div>
            <dt className="text-xs text-muted-foreground">Category</dt>
            <dd className="truncate">
              <Badge variant="outline">{getDocumentCategoryLabel(document.category)}</Badge>
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">File Size</dt>
            <dd className="truncate">{formatFileSize(document.file_size_bytes)}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Uploaded By</dt>
            <dd className="truncate">{document.uploaded_by_name}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Upload Date</dt>
            <dd>{formatDate(document.uploaded_at)}</dd>
          </div>
        </dl>

        <div className="flex gap-2 pt-1">
          <Button variant="outline" size="sm" className="flex-1" asChild>
            <Link href={`/dashboard/documents/${document.document_id}`}>View</Link>
          </Button>
          {isDocumentEditable(document.status) && (
            <Button variant="outline" size="sm" className="flex-1" asChild>
              <Link href={`/dashboard/documents/${document.document_id}/edit`}>Edit</Link>
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            className="shrink-0"
            aria-label={`Download ${document.original_filename}`}
            onClick={() => showSimulatedDownloadToast(document)}
          >
            <Download className="size-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
