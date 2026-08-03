import { CalendarOff } from "lucide-react";
import Link from "next/link";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Button } from "@/components/ui/button";
import type { MedicalDocumentDetail } from "@/lib/mock/documents";

// `visit_id` is a real, but optional, FK on `MedicalDocument` — most
// documents (e.g. an insurance card, a consent form) aren't tied to any
// particular visit, so this section has a real "none" state rather than
// always resolving to something.
export function RelatedVisitSection({ document }: { document: MedicalDocumentDetail }) {
  return (
    <SectionCard title="Related Visit">
      {!document.visit_id ? (
        <EmptyState icon={CalendarOff} title="Not linked to a visit" />
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-medium">{document.visit_number}</p>
            <p className="text-xs text-muted-foreground">Uploaded during this visit</p>
          </div>
          <Button variant="outline" size="sm" asChild>
            <Link href={`/dashboard/visits/${document.visit_id}`}>View Visit</Link>
          </Button>
        </div>
      )}
    </SectionCard>
  );
}
