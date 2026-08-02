import { cn } from "@/lib/utils";

export interface ClinicalNotePreviewField {
  label?: string;
  value: string | null;
}

interface ClinicalNotePreviewProps {
  fields: ClinicalNotePreviewField[];
  emptyMessage?: string;
}

// Read-only, formatted rendering of long-form clinical note content —
// the counterpart to `ClinicalNoteEditor`. Reused across the detail
// page's Clinical Narrative, Assessment, and Plan sections, the Related
// SOAP Note section, and the create/edit page's "Preview" tab (so a
// clinician can see how their in-progress note will read before saving)
// — one component, five call sites, rather than near-duplicate prose
// rendering in each.
export function ClinicalNotePreview({
  fields,
  emptyMessage = "Not documented.",
}: ClinicalNotePreviewProps) {
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
          <p className={cn("whitespace-pre-wrap text-sm", field.label && "mt-1")}>
            {field.value || <span className="text-muted-foreground">Not documented.</span>}
          </p>
        </div>
      ))}
    </div>
  );
}
