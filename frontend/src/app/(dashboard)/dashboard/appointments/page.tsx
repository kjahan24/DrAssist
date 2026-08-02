import type { Metadata } from "next";

import { AppointmentListContent } from "@/features/appointments/components/appointment-list-content";

export const metadata: Metadata = { title: "Appointments" };

export default function AppointmentsPage() {
  return <AppointmentListContent />;
}
