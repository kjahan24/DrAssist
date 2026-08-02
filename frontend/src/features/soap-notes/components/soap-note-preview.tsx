export interface SoapNotePreviewField {
  label?: string;
  value: string | null;
}

interface SoapNotePreviewProps {
  fields: SoapNotePreviewField[];
  emptyMessage?: string;
}

// Read-only, formatted rendering of a SOAP quadrant's content — the
// counterpart to `SoapNoteEditor`. Reused inside each `SoapSectionCard`
// on the detail page and inside the create/edit page's "Preview" tab,
// so a clinician can see how their in-progress note will read before
// saving.
export function SoapNotePreview({
  fields,
  emptyMessage = "Not documented.",
}: SoapNotePreviewProps) {
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
