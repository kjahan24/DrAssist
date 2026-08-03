import Link from "next/link";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import type { ClinicalNote } from "@/lib/mock/clinical-notes";
import { getInitials } from "@/lib/utils";

// The combined avatar + name identity cell for the "Patient" column —
// used as `clinical-note-columns.tsx`'s cell renderer and reused as-is
// in `ClinicalNoteCard` for the mobile layout. Links to the patient's
// own record.
export function ClinicalNotePatientIdentity({
  note,
}: {
  note: Pick<ClinicalNote, "patient_id" | "patient_name" | "patient_number">;
}) {
  return (
    <Link
      href={`/dashboard/patients/${note.patient_id}`}
      className="flex items-center gap-3 rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <Avatar className="size-9">
        <AvatarFallback>{getInitials(note.patient_name)}</AvatarFallback>
      </Avatar>
      <div className="min-w-0">
        <p className="truncate text-sm font-medium">{note.patient_name}</p>
        <p className="truncate text-xs text-muted-foreground">{note.patient_number}</p>
      </div>
    </Link>
  );
}
