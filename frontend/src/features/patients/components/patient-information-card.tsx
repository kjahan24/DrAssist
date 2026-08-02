import type { ReactNode } from "react";

import { SectionCard } from "@/components/dashboard/section-card";

export interface InformationField {
  label: string;
  value: ReactNode;
}

interface PatientInformationCardProps {
  title: string;
  description?: string;
  fields: InformationField[];
  emptyMessage?: string;
}

// A generic titled key-value grid — used for every simple "facts" section
// on the patient detail page (Basic Information, Contact Information,
// Emergency Contact, Insurance). An empty `fields` array means the whole
// section has no data (e.g. no emergency contact on file) and shows one
// message instead of an empty grid; an individual falsy field value
// shows "—" instead.
export function PatientInformationCard({
  title,
  description,
  fields,
  emptyMessage = "Not on file.",
}: PatientInformationCardProps) {
  return (
    <SectionCard title={title} description={description}>
      {fields.length === 0 ? (
        <p className="text-sm text-muted-foreground">{emptyMessage}</p>
      ) : (
        <dl className="grid gap-4 sm:grid-cols-2">
          {fields.map((field) => (
            <div key={field.label}>
              <dt className="text-sm text-muted-foreground">{field.label}</dt>
              <dd className="text-sm font-medium">
                {field.value || <span className="text-muted-foreground">—</span>}
              </dd>
            </div>
          ))}
        </dl>
      )}
    </SectionCard>
  );
}
