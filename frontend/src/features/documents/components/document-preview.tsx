import { getDocumentMimeIcon } from "@/features/documents/lib/document-visuals";
import { cn } from "@/lib/utils";

interface DocumentPreviewProps {
  mimeType: string;
  extension: string;
  className?: string;
}

// The small, compact icon-based preview reused inside `DocumentCard`
// and the list table's "Document Name" cell — a lightweight stand-in
// for a real thumbnail/rendered preview, since no file bytes are ever
// actually stored in this mock. `DocumentViewer` is this preview's
// larger, dedicated counterpart on the detail page's Preview Panel.
export function DocumentPreview({ mimeType, extension, className }: DocumentPreviewProps) {
  const Icon = getDocumentMimeIcon(mimeType);

  return (
    <div
      className={cn(
        "relative flex size-10 shrink-0 items-center justify-center rounded-md bg-muted",
        className,
      )}
      aria-hidden="true"
    >
      <Icon className="size-5 text-muted-foreground" />
      <span className="absolute -bottom-1 -right-1 rounded bg-background px-1 text-[9px] font-semibold leading-tight text-muted-foreground shadow-sm">
        {extension.toUpperCase().slice(0, 4)}
      </span>
    </div>
  );
}
