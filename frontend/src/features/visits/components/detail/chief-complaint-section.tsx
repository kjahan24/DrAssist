import { SectionCard } from "@/components/dashboard/section-card";
import type { VisitDetail } from "@/lib/mock/visits";

export function ChiefComplaintSection({ visit }: { visit: VisitDetail }) {
  return (
    <SectionCard title="Chief Complaint">
      <div className="space-y-4">
        <p className="text-sm">
          {visit.chief_complaint_summary || (
            <span className="text-muted-foreground">Not recorded.</span>
          )}
        </p>
        {visit.notes && (
          <div>
            <p className="text-xs font-medium text-muted-foreground">Notes</p>
            <p className="mt-1 whitespace-pre-wrap text-sm">{visit.notes}</p>
          </div>
        )}
      </div>
    </SectionCard>
  );
}
