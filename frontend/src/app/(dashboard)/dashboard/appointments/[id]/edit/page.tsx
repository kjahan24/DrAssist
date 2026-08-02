import type { Metadata } from "next";

import { AppointmentEditContent } from "@/features/appointments/components/appointment-edit-content";

export const metadata: Metadata = { title: "Edit Appointment" };

export default async function EditAppointmentPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <AppointmentEditContent appointmentId={id} />;
}
