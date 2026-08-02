import type { ReactNode } from "react";

import { SectionCard } from "@/components/dashboard/section-card";

export interface InformationField {
  label: string;
  value: ReactNode;
}

interface SoapNoteDetailsCardProps {
  title: string;
  description?: string;
  actions?: ReactNode;
  fields: InformationField[];
  emptyMessage?: string;
}

// A generic titled key-value grid — used for every short "facts" section
// on the SOAP note detail page (Patient/Doctor/Visit Summary, Clinical
// Note Reference, Audit Information). An empty `fields` array means the
// whole section has no data and shows one message instead of an empty
// grid; an individual falsy field value shows "—" instead.
export function SoapNoteDetailsCard({
  title,
  description,
  actions,
  fields,
  emptyMessage = "Not available.",
}: SoapNoteDetailsCardProps) {
  return (
    <SectionCard title={title} description={description} actions={actions}>
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
