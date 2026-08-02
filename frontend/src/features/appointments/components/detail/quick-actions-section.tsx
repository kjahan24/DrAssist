"use client";

import { useState } from "react";
import {
  CalendarClock,
  CheckCheck,
  CheckCircle2,
  LogIn,
  PlayCircle,
  UserX,
  XCircle,
  type LucideIcon,
} from "lucide-react";

import { SectionCard } from "@/components/dashboard/section-card";
import { Button } from "@/components/ui/button";
import { useChangeAppointmentStatus } from "@/features/appointments/hooks/use-appointments";
import {
  getAllowedTransitions,
  getStatusLabel,
  type AppointmentStatus,
} from "@/lib/mock/appointments";

// Every action here is a real transition from `getAllowedTransitions()`,
// which mirrors the backend's `Appointment._ALLOWED_TRANSITIONS` exactly
// — this menu can never offer a transition the real backend would reject.
// `scheduled` is included only for type completeness (`Record` requires
// every `AppointmentStatus` key); nothing ever transitions back to it.
const ACTION_CONFIG: Record<
  AppointmentStatus,
  { label: string; icon: LucideIcon; variant: "default" | "outline" | "destructive" }
> = {
  scheduled: { label: "Mark Scheduled", icon: CalendarClock, variant: "outline" },
  confirmed: { label: "Confirm", icon: CheckCircle2, variant: "default" },
  checked_in: { label: "Check In", icon: LogIn, variant: "outline" },
  in_progress: { label: "Start Visit", icon: PlayCircle, variant: "default" },
  completed: { label: "Complete", icon: CheckCheck, variant: "default" },
  cancelled: { label: "Cancel", icon: XCircle, variant: "destructive" },
  no_show: { label: "Mark No-Show", icon: UserX, variant: "destructive" },
};

export function QuickActionsSection({
  appointmentId,
  status,
}: {
  appointmentId: string;
  status: AppointmentStatus;
}) {
  const changeStatus = useChangeAppointmentStatus(appointmentId);
  const [pendingTarget, setPendingTarget] = useState<AppointmentStatus | null>(null);
  const allowedTransitions = getAllowedTransitions(status);

  function handleTransition(target: AppointmentStatus) {
    setPendingTarget(target);
    changeStatus.mutate({ status: target }, { onSettled: () => setPendingTarget(null) });
  }

  return (
    <SectionCard
      title="Quick Actions"
      description={`Currently ${getStatusLabel(status).toLowerCase()}.`}
    >
      {allowedTransitions.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          This appointment is in a final state — no further actions are available.
        </p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {allowedTransitions.map((target) => {
            const config = ACTION_CONFIG[target];
            const Icon = config.icon;
            const isPending = changeStatus.isPending && pendingTarget === target;
            return (
              <Button
                key={target}
                variant={config.variant}
                size="sm"
                disabled={changeStatus.isPending}
                onClick={() => handleTransition(target)}
              >
                <Icon className="size-4" />
                {isPending ? "Saving..." : config.label}
              </Button>
            );
          })}
        </div>
      )}
    </SectionCard>
  );
}
