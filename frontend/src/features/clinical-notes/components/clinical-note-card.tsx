import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ClinicalNotePatientIdentity } from "@/features/clinical-notes/components/clinical-note-patient-identity";
import { ClinicalNoteStatusBadge } from "@/features/clinical-notes/components/clinical-note-status-badge";
import { formatDate, formatDateTime } from "@/lib/format";
import { isClinicalNoteEditable, type ClinicalNote } from "@/lib/mock/clinical-notes";

// The mobile-breakpoint counterpart to `ClinicalNoteTable` — shown below
// `md`, where `ClinicalNoteListContent` hides the data table.
export function ClinicalNoteCard({ note }: { note: ClinicalNote }) {
  return (
    <Card>
      <CardContent className="space-y-3 pt-6">
        <div className="flex items-center justify-between gap-2">
          <ClinicalNotePatientIdentity note={note} />
          <ClinicalNoteStatusBadge status={note.status} />
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
          <div>
            <dt className="text-xs text-muted-foreground">Last Updated</dt>
            <dd>{formatDateTime(note.updated_at)}</dd>
          </div>
        </dl>
        <div className="flex gap-2 pt-1">
          <Button variant="outline" size="sm" className="flex-1" asChild>
            <Link href={`/dashboard/clinical-notes/${note.clinical_note_id}`}>View</Link>
          </Button>
          {isClinicalNoteEditable(note.status) && (
            <Button variant="outline" size="sm" className="flex-1" asChild>
              <Link href={`/dashboard/clinical-notes/${note.clinical_note_id}/edit`}>Edit</Link>
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
