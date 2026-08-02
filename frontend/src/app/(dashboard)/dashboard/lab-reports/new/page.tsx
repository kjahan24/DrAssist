import type { Metadata } from "next";

import { LabReportCreateContent } from "@/features/lab-reports/components/lab-report-create-content";

export const metadata: Metadata = { title: "New Lab Report" };

export default function NewLabReportPage() {
  return <LabReportCreateContent />;
}
