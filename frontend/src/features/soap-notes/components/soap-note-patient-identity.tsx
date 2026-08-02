import Link from "next/link";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import type { SOAPNote } from "@/lib/mock/soap-notes";

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((part) => part[0] ?? "")
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

// The combined avatar + name identity cell for the "Patient" column —
// used as `soap-note-columns.tsx`'s cell renderer and reused as-is in
// `SoapNoteCard` for the mobile layout. Links to the patient's own
// record.
export function SoapNotePatientIdentity({
  note,
}: {
  note: Pick<SOAPNote, "patient_id" | "patient_name" | "patient_number">;
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
