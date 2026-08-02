import type { Metadata } from "next";

import { AppointmentCreateContent } from "@/features/appointments/components/appointment-create-content";

export const metadata: Metadata = { title: "New Appointment" };

export default function NewAppointmentPage() {
  return <AppointmentCreateContent />;
}
