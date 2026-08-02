import type { Metadata } from "next";

import { VisitListContent } from "@/features/visits/components/visit-list-content";

export const metadata: Metadata = { title: "Visits" };

export default function VisitsPage() {
  return <VisitListContent />;
}
