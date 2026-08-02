import type { Metadata } from "next";

import { LabReportDetailContent } from "@/features/lab-reports/components/lab-report-detail-content";

export const metadata: Metadata = { title: "Lab Report Details" };

export default async function LabReportDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <LabReportDetailContent labReportId={id} />;
}
