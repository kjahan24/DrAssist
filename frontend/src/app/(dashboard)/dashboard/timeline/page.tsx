import type { Metadata } from "next";

import { TimelinePatientPicker } from "@/features/timeline/components/timeline-patient-picker";

export const metadata: Metadata = { title: "Health Timeline" };

export default function TimelinePage() {
  return <TimelinePatientPicker />;
}
