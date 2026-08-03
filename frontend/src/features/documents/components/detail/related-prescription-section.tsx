"use client";

import { Pill } from "lucide-react";
import Link from "next/link";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { usePrescriptionByVisit } from "@/features/prescriptions/hooks/use-prescriptions";
import type { MedicalDocumentDetail } from "@/lib/mock/documents";

// `MedicalDocument` has no direct FK to a prescription — derived via
// the shared `visit_id` it does carry, same indirection this app
// already uses elsewhere (see `getPrescriptionByVisitId()`'s docstring
// in `lib/mock/prescriptions.ts`).
export function RelatedPrescriptionSection({ document }: { document: MedicalDocumentDetail }) {
  const { data: prescription, isLoading } = usePrescriptionByVisit(document.visit_id ?? "");

  return (
    <SectionCard title="Related Prescription">
      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      ) : !prescription ? (
        <EmptyState icon={Pill} title="No prescription for this document's visit" />
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-medium">{prescription.prescription_number}</p>
            <p className="text-xs text-muted-foreground">Issued for {prescription.patient_name}</p>
          </div>
          <Button variant="outline" size="sm" asChild>
            <Link href={`/dashboard/prescriptions/${prescription.prescription_id}`}>
              View Prescription
            </Link>
          </Button>
        </div>
      )}
    </SectionCard>
  );
}
