"use client";

import { AlertTriangle, Lock } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { PageHeader } from "@/components/dashboard/page-header";
import { PageSkeleton } from "@/components/dashboard/page-skeleton";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Button } from "@/components/ui/button";
import { LabReportForm } from "@/features/lab-reports/components/lab-report-form";
import { useLabReport, useUpdateLabReport } from "@/features/lab-reports/hooks/use-lab-reports";
import {
  getLabReportStatusLabel,
  isLabReportEditable,
  labReportToFormInput,
  type LabReportFormInput,
} from "@/lib/mock/lab-reports";

export function LabReportEditContent({ labReportId }: { labReportId: string }) {
  const router = useRouter();
  const { data: report, isLoading } = useLabReport(labReportId);
  const updateReport = useUpdateLabReport(labReportId);

  if (isLoading) {
    return <PageSkeleton title="Edit Lab Report" />;
  }

  if (!report) {
    return (
      <EmptyState
        titleAs="h1"
        icon={AlertTriangle}
        title="Lab report not found"
        description="This report may have been removed, or the link is incorrect."
      />
    );
  }

  // A Final (or Cancelled/Ordered/Collected) lab report is treated as
  // immutable, mirroring the real, strict Draft-only editability of
  // both `LabOrder` and `LabResult` — see `lib/mock/lab-reports.ts`'s
  // docstring.
  if (!isLabReportEditable(report.status)) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Edit Lab Report"
          description={`${report.report_number} is no longer editable.`}
        />
        <EmptyState
          icon={Lock}
          title={`This report is ${getLabReportStatusLabel(report.status).toLowerCase()}`}
          description="Reports past the draft stage cannot be edited, matching the real lab workflow."
          action={
            <Button variant="outline" asChild>
              <Link href={`/dashboard/lab-reports/${labReportId}`}>View Report</Link>
            </Button>
          }
        />
      </div>
    );
  }

  function handleSubmit(values: LabReportFormInput, status: "draft" | "final") {
    updateReport.mutate(
      { input: values, status },
      {
        onSuccess: () => {
          router.push(`/dashboard/lab-reports/${labReportId}`);
        },
      },
    );
  }

  return (
    <div className="max-w-4xl space-y-6">
      <PageHeader
        title="Edit Lab Report"
        description={`Update ${report.report_number} for ${report.patient_name}.`}
      />
      <LabReportForm
        defaultValues={labReportToFormInput(report)}
        onSubmit={handleSubmit}
        isSubmitting={updateReport.isPending}
      />
    </div>
  );
}
