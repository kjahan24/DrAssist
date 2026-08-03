import { Download } from "lucide-react";

import { SectionCard } from "@/components/dashboard/section-card";
import { Button } from "@/components/ui/button";
import { getDocumentMimeIcon } from "@/features/documents/lib/document-visuals";
import { showSimulatedDownloadToast } from "@/features/documents/lib/simulated-download";
import { formatFileSize } from "@/lib/format";
import type { MedicalDocumentDetail } from "@/lib/mock/documents";

// The large, dedicated "Preview Panel" on the document detail page —
// `DocumentPreview`'s bigger counterpart. No file bytes are ever
// actually stored in this mock, so this renders a placeholder surface
// (icon + filename + metadata) rather than a real rendered file, with a
// Download action that's simulated via `showSimulatedDownloadToast`.
export function DocumentViewer({ document }: { document: MedicalDocumentDetail }) {
  const Icon = getDocumentMimeIcon(document.mime_type);

  return (
    <SectionCard
      title="Preview Panel"
      actions={
        <Button variant="outline" size="sm" onClick={() => showSimulatedDownloadToast(document)}>
          <Download className="size-4" />
          Download
        </Button>
      }
    >
      <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed bg-muted/30 p-12 text-center">
        <div className="flex size-16 items-center justify-center rounded-full bg-muted">
          <Icon className="size-8 text-muted-foreground" aria-hidden="true" />
        </div>
        <div className="space-y-1">
          <p className="text-sm font-medium">{document.original_filename}</p>
          <p className="text-xs text-muted-foreground">
            {document.mime_type} · {formatFileSize(document.file_size_bytes)}
          </p>
        </div>
        <p className="max-w-sm text-xs text-muted-foreground">
          A full in-browser preview isn&apos;t available in this environment. Use Download to
          retrieve the original file.
        </p>
      </div>
    </SectionCard>
  );
}
