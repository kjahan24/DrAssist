import { FileStack } from "lucide-react";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import { formatDate, formatFileSize } from "@/lib/format";
import type { VisitDetail } from "@/lib/mock/visits";

export function DocumentsSection({ visit }: { visit: VisitDetail }) {
  return (
    <SectionCard title="Medical Documents" description="Files attached to this visit.">
      {visit.documents.length === 0 ? (
        <EmptyState icon={FileStack} title="No documents on file" />
      ) : (
        <ul className="divide-y">
          {visit.documents.map((document) => (
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
