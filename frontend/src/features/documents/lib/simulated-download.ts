import { toast } from "sonner";

import type { MedicalDocument } from "@/lib/mock/documents";

// Shared by `DocumentCard`/`document-columns.tsx`'s Download action and
// `DocumentViewer`'s Preview Panel — no file bytes are ever stored in
// this mock, so "downloading" is purely decorative feedback via the
// already-mounted global `Toaster` (see `app/providers.tsx`).
export function showSimulatedDownloadToast(document: Pick<MedicalDocument, "original_filename">) {
  toast.success(`Downloading ${document.original_filename}`, {
    description: "This is a simulated download — no backend request was made.",
  });
}
