import { ClinicalNoteDetailsCard } from "@/features/clinical-notes/components/clinical-note-details-card";
import { formatDateTime } from "@/lib/format";
import type { ClinicalNoteDetail } from "@/lib/mock/clinical-notes";

export function AuditInformationSection({ note }: { note: ClinicalNoteDetail }) {
  return (
    <ClinicalNoteDetailsCard
      title="Audit Information"
      fields={[
        {
          label: "Created",
          value: `${formatDateTime(note.created_at)} by ${note.created_by_name}`,
        },
        {
          label: "Last Updated",
          value: `${formatDateTime(note.updated_at)} by ${note.updated_by_name}`,
        },
        {
          label: "AI Generated",
          value: note.ai_generated ? `Yes (${note.ai_model ?? "unknown model"})` : "No",
        },
        {
          label: "Signed",
          value: note.signed_at
            ? `${formatDateTime(note.signed_at)} by ${note.signed_by_name}`
            : null,
        },
        { label: "Locked", value: note.locked_at ? formatDateTime(note.locked_at) : null },
      ]}
    />
  );
}
