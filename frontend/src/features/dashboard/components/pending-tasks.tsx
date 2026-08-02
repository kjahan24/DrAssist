import {
  CheckCircle2,
  FileStack,
  FileText,
  FlaskConical,
  Pill,
  type LucideIcon,
} from "lucide-react";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate } from "@/lib/format";
import type { PendingTask, PendingTaskType } from "@/lib/mock/doctor-dashboard";

const TASK_ICON: Record<PendingTaskType, LucideIcon> = {
  soap_note: FileText,
  lab_review: FlaskConical,
  prescription_signature: Pill,
  document_review: FileStack,
};

const PRIORITY_VARIANT: Record<PendingTask["priority"], "secondary" | "default" | "destructive"> = {
  low: "secondary",
  medium: "default",
  high: "destructive",
};

interface PendingTasksProps {
  tasks: PendingTask[];
  isLoading?: boolean;
}

export function PendingTasks({ tasks, isLoading }: PendingTasksProps) {
  return (
    <SectionCard title="Pending Tasks" description="Items that need your attention.">
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-14 w-full" />
          ))}
        </div>
      ) : tasks.length === 0 ? (
        <EmptyState
          icon={CheckCircle2}
          title="All caught up"
          description="No pending tasks right now."
        />
      ) : (
        <ul className="space-y-3">
          {tasks.map((task) => {
            const Icon = TASK_ICON[task.type];
            return (
              <li key={task.task_id} className="flex items-start gap-3 rounded-lg border p-3">
                <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                <div className="min-w-0 flex-1 space-y-0.5">
                  <p className="text-sm font-medium">{task.title}</p>
                  <p className="text-xs text-muted-foreground">
                    {task.patient_name} · Due {formatDate(task.due_date)}
                  </p>
                </div>
                <Badge variant={PRIORITY_VARIANT[task.priority]} className="shrink-0 capitalize">
                  {task.priority}
                </Badge>
              </li>
            );
          })}
        </ul>
      )}
    </SectionCard>
  );
}
