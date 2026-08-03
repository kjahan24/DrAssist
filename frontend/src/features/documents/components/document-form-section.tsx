interface DocumentFormSectionProps {
  title: string;
  description?: string;
  children: React.ReactNode;
}

// A <fieldset>/<legend> grouping for the document upload/edit form,
// mirroring `features/prescriptions/components/prescription-form-section.tsx`'s
// reasoning (real fieldset semantics for assistive tech).
export function DocumentFormSection({ title, description, children }: DocumentFormSectionProps) {
  return (
    <fieldset className="space-y-4 rounded-lg border p-4 sm:p-6">
      <legend className="px-1 text-sm font-semibold">{title}</legend>
      {description && <p className="mb-2 text-sm text-muted-foreground">{description}</p>}
      <div className="grid gap-4 sm:grid-cols-2">{children}</div>
    </fieldset>
  );
}
