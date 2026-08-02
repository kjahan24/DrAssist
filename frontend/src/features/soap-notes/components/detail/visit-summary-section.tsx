import Link from "next/link";

import { Button } from "@/components/ui/button";
import { SoapNoteDetailsCard } from "@/features/soap-notes/components/soap-note-details-card";
import type { SOAPNoteDetail } from "@/lib/mock/soap-notes";

export function VisitSummarySection({ note }: { note: SOAPNoteDetail }) {
  return (
    <SoapNoteDetailsCard
      title="Visit Summary"
      actions={
        <Button variant="outline" size="sm" asChild>
          <Link href={`/dashboard/visits/${note.visit_id}`}>View Visit</Link>
        </Button>
      }
      fields={[{ label: "Visit ID", value: note.visit_number }]}
    />
  );
}
