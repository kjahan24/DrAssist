interface PatientFormSectionProps {
  title: string;
  description?: string;
  children: React.ReactNode;
}

// A <fieldset>/<legend> grouping, deliberately distinct from
// `SectionCard` (a page-level <Card> wrapper): grouping *form fields*
// benefits from real fieldset/legend semantics for assistive tech, which
// a <Card> with a heading does not provide.
export function PatientFormSection({ title, description, children }: PatientFormSectionProps) {
  return (
    <fieldset className="space-y-4 rounded-lg border p-4 sm:p-6">
      <legend className="px-1 text-sm font-semibold">{title}</legend>
      {description && <p className="mb-2 text-sm text-muted-foreground">{description}</p>}
      <div className="grid gap-4 sm:grid-cols-2">{children}</div>
    </fieldset>
  );
}
