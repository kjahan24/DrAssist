import { FileStack } from "lucide-react";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import { formatDate, formatFileSize } from "@/lib/format";
import type { ClinicalNoteDetail } from "@/lib/mock/clinical-notes";

// The real backend has no clinical-note-specific attachment entity —
// `VisitAttachment` is keyed strictly by `visit_id` — so this shows the
// parent visit's attachments (`note.attachments`, resolved via
// `note.visit_id` in `lib/mock/clinical-notes.ts`'s seed data).
export function AttachmentsSection({ note }: { note: ClinicalNoteDetail }) {
  return (
    <SectionCard title="Attachments Summary" description="Files attached to this visit.">
      {note.attachments.length === 0 ? (
        <EmptyState icon={FileStack} title="No attachments on file" />
      ) : (
        <ul className="divide-y">
          {note.attachments.map((document) => (
            <li
              key={document.document_id}
              className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0"
            >
              <div className="min-w-0 space-y-0.5">
                <p className="truncate text-sm font-medium">{document.file_name}</p>
                <p className="text-xs text-muted-foreground">
                  {formatFileSize(document.file_size_bytes)}
                </p>
              </div>
              <span className="shrink-0 text-xs text-muted-foreground">
                {formatDate(document.uploaded_at)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </SectionCard>
  );
}
