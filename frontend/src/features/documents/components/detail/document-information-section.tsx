import { Badge } from "@/components/ui/badge";
import { DocumentDetailsCard } from "@/features/documents/components/document-details-card";
import { formatFileSize } from "@/lib/format";
import { getDocumentCategoryLabel, type MedicalDocumentDetail } from "@/lib/mock/documents";

// Folds the task's separate "Category" section into this one — it's a
// single field, so it's shown as a badge inside the same facts grid
// rather than warranting its own titled card.
export function DocumentInformationSection({ document }: { document: MedicalDocumentDetail }) {
  return (
    <DocumentDetailsCard
      title="Document Information"
      fields={[
        { label: "Document ID", value: document.document_number },
        {
          label: "Category",
          value: <Badge variant="outline">{getDocumentCategoryLabel(document.category)}</Badge>,
        },
        { label: "Original Filename", value: document.original_filename },
        { label: "File Type", value: document.mime_type },
        { label: "File Size", value: formatFileSize(document.file_size_bytes) },
        { label: "Description", value: document.description },
      ]}
    />
  );
}
