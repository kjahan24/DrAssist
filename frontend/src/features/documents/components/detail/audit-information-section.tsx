import { DocumentDetailsCard } from "@/features/documents/components/document-details-card";
import { getDocumentStatusLabel } from "@/lib/mock/documents";
import { formatDateTime } from "@/lib/format";
import type { MedicalDocumentDetail } from "@/lib/mock/documents";

// `MedicalDocument` has no separate created/updated timestamps in the
// real backend (each row is written once at `uploaded_at`, since there's
// no "edit history" concept beyond the metadata fields this module's
// Edit form can change) — this shows what's actually real: who
// uploaded it, when, its current lifecycle status, and where it's
// stored.
export function AuditInformationSection({ document }: { document: MedicalDocumentDetail }) {
  return (
    <DocumentDetailsCard
      title="Audit Information"
      fields={[
        {
          label: "Uploaded",
          value: `${formatDateTime(document.uploaded_at)} by ${document.uploaded_by_name}`,
        },
        { label: "Status", value: getDocumentStatusLabel(document.status) },
        { label: "Storage Provider", value: document.storage_provider },
      ]}
    />
  );
}
