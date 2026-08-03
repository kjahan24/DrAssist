import { CardSkeleton } from "@/components/shared/states/card-skeleton";
import { DocumentCard } from "@/features/documents/components/document-card";
import type { MedicalDocument } from "@/lib/mock/documents";

interface DocumentGridProps {
  documents: MedicalDocument[];
  isLoading?: boolean;
}

// The Grid-view counterpart to `DocumentTable` — visible at every
// breakpoint (unlike the table's mobile-card stack, which only shows
// below `md`), since a document grid is a reasonable primary layout on
// any screen size.
export function DocumentGrid({ documents, isLoading }: DocumentGridProps) {
  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, index) => (
          <CardSkeleton key={index} />
        ))}
      </div>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {documents.map((document) => (
        <DocumentCard key={document.document_id} document={document} />
      ))}
    </div>
  );
}
