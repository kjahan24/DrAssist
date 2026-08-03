"use client";

import { FileText } from "lucide-react";
import Link from "next/link";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useClinicalNoteByVisit } from "@/features/clinical-notes/hooks/use-clinical-notes";
import type { MedicalDocumentDetail } from "@/lib/mock/documents";

// `MedicalDocument` has no direct FK to a clinical note — derived via
// the shared `visit_id` it does carry, same indirection this app
// already uses elsewhere (see `getClinicalNoteByVisitId()`'s docstring
// in `lib/mock/documents.ts`).
export function RelatedClinicalNoteSection({ document }: { document: MedicalDocumentDetail }) {
  const { data: clinicalNote, isLoading } = useClinicalNoteByVisit(document.visit_id ?? "");

  return (
    <SectionCard title="Related Clinical Note">
      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      ) : !clinicalNote ? (
        <EmptyState icon={FileText} title="No clinical note for this document's visit" />
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-medium">{clinicalNote.note_number}</p>
            <p className="text-xs text-muted-foreground">
              Documented for {clinicalNote.patient_name}
            </p>
          </div>
          <Button variant="outline" size="sm" asChild>
            <Link href={`/dashboard/clinical-notes/${clinicalNote.clinical_note_id}`}>
              View Clinical Note
            </Link>
          </Button>
        </div>
      )}
    </SectionCard>
  );
}
