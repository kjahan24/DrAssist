import { CheckCircle2, Clock, Mail, ShieldOff, XCircle } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { formatDateTime } from "@/lib/format";
import {
  getFamilyAccessStatusLabel,
  type FamilyAccessHistoryEntry,
} from "@/lib/mock/family-members";
import { cn } from "@/lib/utils";

const STATUS_ICON: Record<FamilyAccessHistoryEntry["status"], LucideIcon> = {
  pending: Mail,
  accepted: CheckCircle2,
  rejected: XCircle,
  revoked: ShieldOff,
  expired: Clock,
};

const STATUS_COLOR: Record<FamilyAccessHistoryEntry["status"], string> = {
  pending: "bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-300",
  accepted: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  rejected: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  revoked: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
  expired: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
};

// Renders one grant's `history` (`FamilyAccessHistoryEntry[]`) as a
// small vertical timeline — used by the "Invitation History" section on
// the Family Member Details page. `history` is generated deterministically
// from each seeded grant's final status (see `lib/mock/family-members.ts`'s
// own docstring on why no queryable transition log exists on the real
// backend), same invented-log reasoning as `AppointmentStatusHistoryEntry`.
export function InvitationTimeline({ entries }: { entries: FamilyAccessHistoryEntry[] }) {
  if (entries.length === 0) {
    return <p className="text-sm text-muted-foreground">No invitation history yet.</p>;
  }

  return (
    <ol className="space-y-0">
      {entries.map((entry, index) => {
        const Icon = STATUS_ICON[entry.status];
        const isLast = index === entries.length - 1;
        return (
          <li
            key={`${entry.status}-${entry.changed_at}`}
            className="relative flex gap-3 pb-5 last:pb-0"
          >
            {!isLast && (
              <span
                className="absolute left-[13px] top-7 h-[calc(100%-1.75rem)] w-px bg-border"
                aria-hidden="true"
              />
            )}
            <div
              className={cn(
                "z-10 flex size-7 shrink-0 items-center justify-center rounded-full ring-4 ring-background",
                STATUS_COLOR[entry.status],
              )}
              aria-hidden="true"
            >
              <Icon className="size-3.5" />
            </div>
            <div className="min-w-0 flex-1 pt-0.5">
              <p className="text-sm font-medium">{getFamilyAccessStatusLabel(entry.status)}</p>
              <p className="text-xs text-muted-foreground">{formatDateTime(entry.changed_at)}</p>
              {entry.note && <p className="mt-0.5 text-sm">{entry.note}</p>}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
