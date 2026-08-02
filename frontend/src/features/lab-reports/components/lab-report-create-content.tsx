"use client";

import { useRouter } from "next/navigation";

import { PageHeader } from "@/components/dashboard/page-header";
import { LabReportForm } from "@/features/lab-reports/components/lab-report-form";
import { useCreateLabReport } from "@/features/lab-reports/hooks/use-lab-reports";
import type { LabReportFormInput } from "@/lib/mock/lab-reports";

export function LabReportCreateContent() {
  const router = useRouter();
  const createReport = useCreateLabReport();

  function handleSubmit(values: LabReportFormInput, status: "draft" | "final") {
    createReport.mutate(
      { input: values, status },
      {
        onSuccess: (report) => {
          router.push(`/dashboard/lab-reports/${report.lab_report_id}`);
        },
      },
    );
  }

  return (
    <div className="max-w-4xl space-y-6">
      <PageHeader title="New Lab Report" description="Order a new laboratory test panel." />
      <LabReportForm onSubmit={handleSubmit} isSubmitting={createReport.isPending} />
    </div>
  );
}
