interface VisitFormSectionProps {
  title: string;
  description?: string;
  children: React.ReactNode;
}

// A <fieldset>/<legend> grouping for the visit form, mirroring
// `features/appointments/components/appointment-form-section.tsx`'s
// reasoning (real fieldset semantics for assistive tech) — kept as its
// own component rather than importing that one, for the same
// separation-of-concerns reasoning already established there.
export function VisitFormSection({ title, description, children }: VisitFormSectionProps) {
  return (
    <fieldset className="space-y-4 rounded-lg border p-4 sm:p-6">
      <legend className="px-1 text-sm font-semibold">{title}</legend>
      {description && <p className="mb-2 text-sm text-muted-foreground">{description}</p>}
      <div className="grid gap-4 sm:grid-cols-2">{children}</div>
    </fieldset>
  );
}
