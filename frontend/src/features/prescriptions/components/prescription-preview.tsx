export interface PrescriptionPreviewField {
  label?: string;
  value: string | null;
}

interface PrescriptionPreviewProps {
  fields: PrescriptionPreviewField[];
  emptyMessage?: string;
}

// Read-only, formatted rendering of long-form prescription text (the
// prescription-level notes) — mirrors
// `ClinicalNotePreview`/`SoapNotePreview`/`LabReportPreview`'s identical
// pattern.
export function PrescriptionPreview({
  fields,
  emptyMessage = "Not documented.",
}: PrescriptionPreviewProps) {
  const hasContent = fields.some((field) => field.value);

  if (!hasContent) {
    return <p className="text-sm text-muted-foreground">{emptyMessage}</p>;
  }

  return (
    <div className="space-y-4">
      {fields.map((field, index) => (
        <div key={field.label ?? index}>
          {field.label && (
            <p className="text-xs font-medium text-muted-foreground">{field.label}</p>
          )}
          <p className="whitespace-pre-wrap text-sm">
            {field.value || <span className="text-muted-foreground">Not documented.</span>}
          </p>
        </div>
      ))}
    </div>
  );
}
