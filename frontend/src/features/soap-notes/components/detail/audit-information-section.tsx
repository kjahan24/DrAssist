import { SoapNoteDetailsCard } from "@/features/soap-notes/components/soap-note-details-card";
import { formatDateTime } from "@/lib/format";
import { getSoapNoteStatusLabel, type SOAPNoteDetail } from "@/lib/mock/soap-notes";

export function AuditInformationSection({ note }: { note: SOAPNoteDetail }) {
  return (
    <SoapNoteDetailsCard
      title="Audit Information"
      fields={[
        { label: "Status", value: getSoapNoteStatusLabel(note.status) },
        {
          label: "Created",
          value: `${formatDateTime(note.created_at)} by ${note.created_by_name}`,
        },
        {
          label: "Last Updated",
          value: `${formatDateTime(note.updated_at)} by ${note.updated_by_name}`,
        },
      ]}
    />
  );
}
