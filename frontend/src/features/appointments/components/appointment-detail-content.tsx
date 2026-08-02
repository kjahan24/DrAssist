"use client";

import { AlertTriangle, Pencil } from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/dashboard/page-header";
import { PageSkeleton } from "@/components/dashboard/page-skeleton";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Button } from "@/components/ui/button";
import { AppointmentStatusBadge } from "@/features/appointments/components/appointment-status-badge";
import { AppointmentTimeline } from "@/features/appointments/components/appointment-timeline";
import { AppointmentInfoSection } from "@/features/appointments/components/detail/appointment-info-section";
import { DoctorInfoSection } from "@/features/appointments/components/detail/doctor-info-section";
import { NotesSection } from "@/features/appointments/components/detail/notes-section";
import { PatientSummarySection } from "@/features/appointments/components/detail/patient-summary-section";
import { QuickActionsSection } from "@/features/appointments/components/detail/quick-actions-section";
import { ReasonForVisitSection } from "@/features/appointments/components/detail/reason-for-visit-section";
import { useAppointment } from "@/features/appointments/hooks/use-appointments";
import { formatDate, formatTime } from "@/lib/format";

export function AppointmentDetailContent({ appointmentId }: { appointmentId: string }) {
  const { data: appointment, isLoading } = useAppointment(appointmentId);

  if (isLoading) {
    return <PageSkeleton title="Appointment Details" />;
  }

  if (!appointment) {
    return (
      <EmptyState
        titleAs="h1"
        icon={AlertTriangle}
        title="Appointment not found"
        description="This appointment may have been removed, or the link is incorrect."
      />
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={appointment.appointment_number}
        description={`${appointment.patient_name} with ${appointment.doctor_name} · ${formatDate(
          appointment.appointment_date,
        )} at ${formatTime(appointment.start_time)}`}
        actions={
          <div className="flex items-center gap-2">
            <AppointmentStatusBadge status={appointment.status} />
            <Button asChild>
              <Link href={`/dashboard/appointments/${appointment.appointment_id}/edit`}>
                <Pencil className="size-4" />
                Edit Appointment
              </Link>
            </Button>
          </div>
        }
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <AppointmentInfoSection appointment={appointment} />
        <PatientSummarySection appointment={appointment} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <DoctorInfoSection appointment={appointment} />
        <QuickActionsSection
          appointmentId={appointment.appointment_id}
          status={appointment.status}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <ReasonForVisitSection appointment={appointment} />
        <NotesSection appointment={appointment} />
      </div>

      <AppointmentTimeline history={appointment.status_history} />
    </div>
  );
}
