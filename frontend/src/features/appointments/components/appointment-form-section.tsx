interface AppointmentFormSectionProps {
  title: string;
  description?: string;
  children: React.ReactNode;
}

// A <fieldset>/<legend> grouping for the appointment form, mirroring
// `features/patients/components/patient-form-section.tsx`'s reasoning
// (real fieldset semantics for assistive tech) — kept as its own
// component rather than importing the patients one, since reaching into
// another feature module for a purely presentational wrapper would be
// unnecessary coupling.
export function AppointmentFormSection({
  title,
  description,
  children,
}: AppointmentFormSectionProps) {
  return (
    <fieldset className="space-y-4 rounded-lg border p-4 sm:p-6">
      <legend className="px-1 text-sm font-semibold">{title}</legend>
      {description && <p className="mb-2 text-sm text-muted-foreground">{description}</p>}
      <div className="grid gap-4 sm:grid-cols-2">{children}</div>
    </fieldset>
  );
}
