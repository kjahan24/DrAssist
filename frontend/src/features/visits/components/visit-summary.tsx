import Link from "next/link";
import type { ReactNode } from "react";

import { SectionCard } from "@/components/dashboard/section-card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";

export interface VisitSummaryField {
  label: string;
  value: ReactNode;
}

interface VisitSummaryProps {
  title: string;
  name: string;
  initials: string;
  fields: VisitSummaryField[];
  href?: string;
  linkLabel?: string;
}

// A compact "who this visit relates to" identity card — shared by both
// the Patient Summary and Doctor Summary detail sections (same shape:
// name, a couple of identifying facts, optional link to the full
// record), rather than two nearly-identical bespoke sections. Distinct
// from `VisitDetailsCard` by design: this one carries an avatar/name
// identity treatment, that one is a plain facts grid.
export function VisitSummary({
  title,
  name,
  initials,
  fields,
  href,
  linkLabel = "View Record",
}: VisitSummaryProps) {
  return (
    <SectionCard
      title={title}
      actions={
        href ? (
          <Button variant="outline" size="sm" asChild>
            <Link href={href}>{linkLabel}</Link>
          </Button>
        ) : undefined
      }
    >
      <div className="flex items-center gap-3">
        <Avatar className="size-10">
          <AvatarFallback>{initials}</AvatarFallback>
        </Avatar>
        <p className="text-sm font-semibold">{name}</p>
      </div>
      {fields.length > 0 && (
        <dl className="mt-4 grid gap-4 sm:grid-cols-2">
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
