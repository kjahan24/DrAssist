import { Paperclip } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { getTimelineEventIcon } from "@/features/timeline/lib/event-visuals";
import { formatDateTime } from "@/lib/format";
import { getTimelineEventTypeLabel, type HealthTimelineEvent } from "@/lib/mock/timeline";

interface TimelineDetailsPanelProps {
  event: HealthTimelineEvent | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// The slide-over panel opened by a `TimelineCard`'s "Details" action —
// shows the full event metadata, its "Related entities" links (computed
// at aggregation time in `lib/mock/timeline.ts`), an attachments
// summary, and a primary action to navigate to the underlying record.
// Every link here is a real route already built by an earlier module —
// "(UI only)" per the task means this panel itself does no additional
// data fetching, not that the links are fake.
export function TimelineDetailsPanel({ event, open, onOpenChange }: TimelineDetailsPanelProps) {
  const Icon = event ? getTimelineEventIcon(event.event_type) : null;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-md">
        {event && (
          <>
            <SheetHeader>
              <SheetTitle className="flex items-center gap-2">
                {Icon && <Icon className="size-5 shrink-0" aria-hidden="true" />}
                {event.title}
              </SheetTitle>
              <SheetDescription>{getTimelineEventTypeLabel(event.event_type)}</SheetDescription>
            </SheetHeader>

            <div className="mt-6 space-y-6">
              <dl className="grid grid-cols-2 gap-4 text-sm">
                <div className="col-span-2">
                  <dt className="text-xs text-muted-foreground">Timestamp</dt>
                  <dd className="font-medium">{formatDateTime(event.occurred_at)}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">Patient</dt>
                  <dd className="font-medium">{event.patient_name}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">Doctor</dt>
                  <dd className="font-medium">{event.doctor_name ?? "—"}</dd>
                </div>
                {event.status_label && (
                  <div>
                    <dt className="text-xs text-muted-foreground">Status</dt>
                    <dd>
                      <Badge variant="outline">{event.status_label}</Badge>
                    </dd>
                  </div>
                )}
                {event.visit_number && (
                  <div>
                    <dt className="text-xs text-muted-foreground">Visit</dt>
                    <dd className="font-medium">{event.visit_number}</dd>
                  </div>
                )}
                {event.summary && (
                  <div className="col-span-2">
                    <dt className="text-xs text-muted-foreground">Summary</dt>
                    <dd>{event.summary}</dd>
                  </div>
                )}
              </dl>

              <div className="space-y-2">
                <h3 className="text-sm font-semibold">Related Entities</h3>
                {event.related.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No related records.</p>
                ) : (
                  <ul className="space-y-1.5">
                    {event.related.map((link) => (
                      <li key={link.href}>
                        <Link
                          href={link.href}
                          className="text-sm text-primary underline-offset-4 hover:underline"
                        >
                          {link.label}
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Paperclip className="size-4" aria-hidden="true" />
                {event.attachment_count > 0
                  ? `${event.attachment_count} attached document${event.attachment_count === 1 ? "" : "s"}`
                  : "No attachments"}
              </div>

              <Button asChild className="w-full">
                <Link href={event.quick_action.href}>{event.quick_action.label}</Link>
              </Button>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
