import type { Metadata } from "next";

import { LabReportEditContent } from "@/features/lab-reports/components/lab-report-edit-content";

export const metadata: Metadata = { title: "Edit Lab Report" };

export default async function EditLabReportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <LabReportEditContent labReportId={id} />;
}
