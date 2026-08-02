import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { SoapNotePatientIdentity } from "@/features/soap-notes/components/soap-note-patient-identity";
import { SoapNoteStatusBadge } from "@/features/soap-notes/components/soap-note-status-badge";
import { formatDate } from "@/lib/format";
import { isSoapNoteEditable, type SOAPNote } from "@/lib/mock/soap-notes";

// The mobile-breakpoint counterpart to `SoapNoteTable` — shown below
// `md`, where `SoapNoteListContent` hides the data table.
export function SoapNoteCard({ note }: { note: SOAPNote }) {
  return (
    <Card>
      <CardContent className="space-y-3 pt-6">
        <div className="flex items-center justify-between gap-2">
          <SoapNotePatientIdentity note={note} />
          <SoapNoteStatusBadge status={note.status} />
        </div>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <div>
            <dt className="text-xs text-muted-foreground">Doctor</dt>
            <dd className="truncate">{note.doctor_name}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Visit</dt>
            <dd className="truncate">{note.visit_number}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Created</dt>
            <dd>{formatDate(note.created_at)}</dd>
          </div>
        </dl>
        <div className="flex gap-2 pt-1">
          <Button variant="outline" size="sm" className="flex-1" asChild>
            <Link href={`/dashboard/soap-notes/${note.soap_note_id}`}>View</Link>
          </Button>
          {isSoapNoteEditable(note.status) && (
            <Button variant="outline" size="sm" className="flex-1" asChild>
              <Link href={`/dashboard/soap-notes/${note.soap_note_id}/edit`}>Edit</Link>
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
