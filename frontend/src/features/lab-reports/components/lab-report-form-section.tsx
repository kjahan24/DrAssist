interface LabReportFormSectionProps {
  title: string;
  description?: string;
  children: React.ReactNode;
}

// A <fieldset>/<legend> grouping for the lab report form, mirroring
// `features/soap-notes/components/soap-note-form-section.tsx`'s
// reasoning (real fieldset semantics for assistive tech) — kept as its
// own component for the same separation-of-concerns reasoning already
// established there. `<legend>` stays the fieldset's direct first
// child (required for it to be recognized as the fieldset's accessible
// name) — any extra per-section controls (like the Test List's "Add
// Test" button) are placed in their own row after it, not merged into
// the same flex row as the legend.
export function LabReportFormSection({ title, description, children }: LabReportFormSectionProps) {
  return (
    <fieldset className="space-y-4 rounded-lg border p-4 sm:p-6">
      <legend className="px-1 text-sm font-semibold">{title}</legend>
      {description && <p className="mb-2 text-sm text-muted-foreground">{description}</p>}
      <div className="grid gap-4 sm:grid-cols-2">{children}</div>
    </fieldset>
  );
}
