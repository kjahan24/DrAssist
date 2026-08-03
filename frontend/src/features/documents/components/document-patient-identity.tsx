import Link from "next/link";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import type { MedicalDocument } from "@/lib/mock/documents";
import { getInitials } from "@/lib/utils";

// The combined avatar + name identity cell for the "Patient" column —
// used as `document-columns.tsx`'s cell renderer and reused as-is in
// `DocumentCard` for the mobile/grid layouts. Links to the patient's
// own record.
export function DocumentPatientIdentity({
  document,
}: {
  document: Pick<MedicalDocument, "patient_id" | "patient_name" | "patient_number">;
}) {
  return (
    <Link
      href={`/dashboard/patients/${document.patient_id}`}
      className="flex items-center gap-3 rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <Avatar className="size-9">
        <AvatarFallback>{getInitials(document.patient_name)}</AvatarFallback>
      </Avatar>
      <div className="min-w-0">
        <p className="truncate text-sm font-medium">{document.patient_name}</p>
        <p className="truncate text-xs text-muted-foreground">{document.patient_number}</p>
      </div>
    </Link>
  );
}
