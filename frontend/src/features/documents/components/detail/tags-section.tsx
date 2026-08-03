import { Tag } from "lucide-react";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Badge } from "@/components/ui/badge";
import type { MedicalDocumentDetail } from "@/lib/mock/documents";

export function TagsSection({ document }: { document: MedicalDocumentDetail }) {
  return (
    <SectionCard title="Tags">
      {document.tags.length === 0 ? (
        <EmptyState icon={Tag} title="No tags added" />
      ) : (
        <div className="flex flex-wrap gap-2">
          {document.tags.map((tag) => (
            <Badge key={tag} variant="secondary">
              {tag}
            </Badge>
          ))}
        </div>
      )}
    </SectionCard>
  );
}
