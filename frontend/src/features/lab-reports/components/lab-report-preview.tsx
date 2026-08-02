export interface LabReportPreviewField {
  label?: string;
  value: string | null;
}

interface LabReportPreviewProps {
  fields: LabReportPreviewField[];
  emptyMessage?: string;
}

// Read-only, formatted rendering of long-form lab report text (the
// report-level interpretation/comments) — used on the detail page's
// Interpretation section and reusable inside the create/edit form if a
// live preview is ever added there, mirroring
// `ClinicalNotePreview`/`SoapNotePreview`'s identical pattern.
export function LabReportPreview({
  fields,
  emptyMessage = "Not documented.",
}: LabReportPreviewProps) {
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
