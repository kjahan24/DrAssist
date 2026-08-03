import { History } from "lucide-react";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import { formatDateTime, formatFileSize } from "@/lib/format";
import type { MedicalDocumentDetail } from "@/lib/mock/documents";

// Presentation-only — the real backend has no versioning concept for
// `MedicalDocument` (each upload is an independent row), see this
// module's own docstring in `lib/mock/documents.ts`. Every seeded
// document currently has exactly one version (its original upload).
export function VersionHistorySection({ document }: { document: MedicalDocumentDetail }) {
  return (
    <SectionCard title="Version History">
      {document.version_history.length === 0 ? (
        <EmptyState icon={History} title="No version history available" />
      ) : (
        <ul className="divide-y">
          {document.version_history.map((version) => (
            <li key={version.version_id} className="space-y-1 py-3 first:pt-0 last:pb-0">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-medium">Version {version.version_number}</p>
                <span className="text-xs text-muted-foreground">
                  {formatFileSize(version.file_size_bytes)}
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                {formatDateTime(version.uploaded_at)} by {version.uploaded_by_name}
              </p>
              {version.note && <p className="text-sm">{version.note}</p>}
            </li>
          ))}
        </ul>
      )}
    </SectionCard>
  );
}
