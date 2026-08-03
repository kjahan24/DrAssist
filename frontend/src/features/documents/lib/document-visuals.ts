import { File, FileImage, FileSpreadsheet, FileText, type LucideIcon } from "lucide-react";

// Presentational only — consolidated here from byte-identical copies in
// `DocumentPreview` and `DocumentViewer` (the compact and large preview
// surfaces for the same document), the same `*-visuals.ts` convention
// `features/timeline/lib/event-visuals.ts` and
// `features/notifications/lib/notification-visuals.ts` already
// establish for keeping icon-resolution logic out of `lib/mock/`.
export function getDocumentMimeIcon(mimeType: string): LucideIcon {
  if (mimeType.startsWith("image/")) return FileImage;
  if (mimeType === "application/pdf" || mimeType.startsWith("text/")) return FileText;
  if (mimeType.includes("spreadsheet") || mimeType.includes("csv")) return FileSpreadsheet;
  return File;
}
