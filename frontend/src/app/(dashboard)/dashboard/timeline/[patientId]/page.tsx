import type { Metadata } from "next";

import { PatientTimelineContent } from "@/features/timeline/components/patient-timeline-content";

export const metadata: Metadata = { title: "Patient Timeline" };

export default async function PatientTimelinePage({
  params,
}: {
  params: Promise<{ patientId: string }>;
}) {
  const { patientId } = await params;
  return <PatientTimelineContent patientId={patientId} />;
}
