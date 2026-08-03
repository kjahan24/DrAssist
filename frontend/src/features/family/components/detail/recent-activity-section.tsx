import { Activity } from "lucide-react";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import { formatDateTime } from "@/lib/format";
import type { FamilyMemberDetail } from "@/lib/mock/family-members";

// No real backend basis (no access-log entity exists yet) — invented
// purely for this task's "Recent Activity" section, seeded only for
// accepted members. See `lib/mock/family-members.ts`'s own docstring.
export function RecentActivitySection({ member }: { member: FamilyMemberDetail }) {
  return (
    <SectionCard title="Recent Activity">
      {member.recent_activity.length === 0 ? (
        <EmptyState icon={Activity} title="No recent activity" />
      ) : (
        <ul className="divide-y">
          {member.recent_activity.map((entry) => (
            <li key={entry.activity_id} className="space-y-0.5 py-3 first:pt-0 last:pb-0">
              <p className="text-sm">{entry.description}</p>
              <p className="text-xs text-muted-foreground">{formatDateTime(entry.occurred_at)}</p>
            </li>
          ))}
        </ul>
      )}
    </SectionCard>
  );
}
