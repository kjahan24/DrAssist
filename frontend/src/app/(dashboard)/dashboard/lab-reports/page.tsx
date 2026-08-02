import type { Metadata } from "next";

import { LabReportListContent } from "@/features/lab-reports/components/lab-report-list-content";

export const metadata: Metadata = { title: "Lab Reports" };

export default function LabReportsPage() {
  return <LabReportListContent />;
}
