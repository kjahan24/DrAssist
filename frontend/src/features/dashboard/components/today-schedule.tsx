import Link from "next/link";
import { CalendarClock } from "lucide-react";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import { TableSkeleton } from "@/components/shared/states/table-skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatDate } from "@/lib/format";
import type { AppointmentStatus, ScheduleAppointment } from "@/lib/mock/doctor-dashboard";

const STATUS_LABEL: Record<AppointmentStatus, string> = {
  scheduled: "Scheduled",
  confirmed: "Confirmed",
  checked_in: "Checked In",
  in_progress: "In Progress",
  completed: "Completed",
  cancelled: "Cancelled",
  no_show: "No Show",
};

const STATUS_VARIANT: Record<
  AppointmentStatus,
  "default" | "secondary" | "outline" | "destructive"
> = {
  scheduled: "outline",
  confirmed: "secondary",
  checked_in: "secondary",
  in_progress: "default",
  completed: "outline",
  cancelled: "destructive",
  no_show: "destructive",
};

interface TodayScheduleProps {
  appointments: ScheduleAppointment[];
  isLoading?: boolean;
}

export function TodaySchedule({ appointments, isLoading }: TodayScheduleProps) {
  return (
    <SectionCard
      title="Today's Schedule"
      description="Your appointments for today."
      actions={
        <Button variant="outline" size="sm" asChild>
          <Link href="/dashboard/schedule">View full schedule</Link>
        </Button>
      }
    >
      {isLoading ? (
        <TableSkeleton rows={5} columns={5} />
      ) : appointments.length === 0 ? (
        <EmptyState
          icon={CalendarClock}
          title="No appointments today"
          description="Your schedule is clear for today."
        />
      ) : (
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Time</TableHead>
                <TableHead>Patient</TableHead>
                <TableHead>Visit Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {appointments.map((appointment) => (
                <TableRow key={appointment.appointment_id}>
                  <TableCell className="whitespace-nowrap font-medium">
                    {formatDate(appointment.scheduled_time, "h:mm a")}
                  </TableCell>
                  <TableCell>{appointment.patient_name}</TableCell>
                  <TableCell>{appointment.visit_type}</TableCell>
                  <TableCell>
                    <Badge variant={STATUS_VARIANT[appointment.status]}>
                      {STATUS_LABEL[appointment.status]}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="sm" asChild>
                      <Link href={`/dashboard/appointments/${appointment.appointment_id}`}>
                        View
                      </Link>
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </SectionCard>
  );
}
