import type { Metadata } from "next";

import { VisitCreateContent } from "@/features/visits/components/visit-create-content";

export const metadata: Metadata = { title: "New Visit" };

export default function NewVisitPage() {
  return <VisitCreateContent />;
}
