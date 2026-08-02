import { FileStack } from "lucide-react";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import { formatDate } from "@/lib/format";
import type { DocumentSummary } from "@/lib/mock/patients";

export function DocumentsSection({ documents }: { documents: DocumentSummary[] }) {
  return (
    <SectionCard title="Medical Documents" description="Recently uploaded files.">
      {documents.length === 0 ? (
        <EmptyState icon={FileStack} title="No documents on file" />
      ) : (
        <ul className="divide-y">
          {documents.map((document) => (
            <li
              key={document.document_id}
              className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0"
            >
              <div className="min-w-0 space-y-0.5">
                <p className="truncate text-sm font-medium">{document.file_name}</p>
                <p className="text-xs text-muted-foreground">{document.category}</p>
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
