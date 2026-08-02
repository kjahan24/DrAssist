import { FileStack } from "lucide-react";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import { formatDate, formatFileSize } from "@/lib/format";
import type { LabReportDetail } from "@/lib/mock/lab-reports";

// The real backend has no lab-specific attachment entity —
// `VisitAttachment` is keyed strictly by `visit_id` — so this shows the
// parent visit's attachments (`report.attachments`, resolved via
// `report.visit_id` in `lib/mock/lab-reports.ts`'s seed data).
export function AttachmentsSection({ report }: { report: LabReportDetail }) {
  return (
    <SectionCard title="Attachments" description="Files attached to this visit.">
      {report.attachments.length === 0 ? (
        <EmptyState icon={FileStack} title="No attachments on file" />
      ) : (
        <ul className="divide-y">
          {report.attachments.map((document) => (
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
