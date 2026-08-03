"use client";

import { FlaskConical } from "lucide-react";
import Link from "next/link";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useLabReportByVisit } from "@/features/lab-reports/hooks/use-lab-reports";
import type { MedicalDocumentDetail } from "@/lib/mock/documents";

// `MedicalDocument` has no direct FK to a lab report — derived via the
// shared `visit_id` it does carry, same indirection this app already
// uses elsewhere (see `getLabReportByVisitId()`'s docstring in
// `lib/mock/lab-reports.ts`).
export function RelatedLabReportSection({ document }: { document: MedicalDocumentDetail }) {
  const { data: labReport, isLoading } = useLabReportByVisit(document.visit_id ?? "");

  return (
    <SectionCard title="Related Lab Report">
      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      ) : !labReport ? (
        <EmptyState icon={FlaskConical} title="No lab report for this document's visit" />
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-medium">{labReport.report_number}</p>
            <p className="text-xs text-muted-foreground">Ordered for {labReport.patient_name}</p>
          </div>
          <Button variant="outline" size="sm" asChild>
            <Link href={`/dashboard/lab-reports/${labReport.lab_report_id}`}>View Lab Report</Link>
          </Button>
        </div>
      )}
    </SectionCard>
  );
}
