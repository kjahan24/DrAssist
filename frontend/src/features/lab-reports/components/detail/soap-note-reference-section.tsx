"use client";

import Link from "next/link";
import { FileText } from "lucide-react";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useSoapNoteByClinicalNote } from "@/features/soap-notes/hooks/use-soap-notes";
import type { LabReportDetail } from "@/lib/mock/lab-reports";

// Neither `LabOrder` nor `LabResult` links to a SOAP Note directly in
// the real backend — this derives it the same way
// `lib/mock/soap-notes.ts` already does for Clinical Notes: SOAP Note
// is one-to-one with Clinical Note, and this report already carries
// `clinical_note_id` directly, so that's the lookup key.
export function SoapNoteReferenceSection({ report }: { report: LabReportDetail }) {
  const { data: soapNote, isLoading } = useSoapNoteByClinicalNote(report.clinical_note_id);

  return (
    <SectionCard title="Related SOAP Note">
      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      ) : !soapNote ? (
        <EmptyState icon={FileText} title="No SOAP note for this clinical note" />
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-medium">{soapNote.soap_number}</p>
            <p className="text-xs text-muted-foreground">Documented for {soapNote.patient_name}</p>
          </div>
          <Button variant="outline" size="sm" asChild>
            <Link href={`/dashboard/soap-notes/${soapNote.soap_note_id}`}>View SOAP Note</Link>
          </Button>
        </div>
      )}
    </SectionCard>
  );
}
