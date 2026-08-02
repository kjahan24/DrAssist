import Link from "next/link";

import { VisitDetailsCard } from "@/features/visits/components/visit-details-card";
import { VisitStatusBadge } from "@/features/visits/components/visit-status-badge";
import { formatDate, formatDateTime } from "@/lib/format";
import { getVisitTypeLabel, type VisitDetail } from "@/lib/mock/visits";

export function VisitInfoSection({ visit }: { visit: VisitDetail }) {
  return (
    <VisitDetailsCard
      title="Visit Information"
      fields={[
        { label: "Visit ID", value: visit.visit_number },
        { label: "Status", value: <VisitStatusBadge status={visit.visit_status} /> },
        { label: "Visit Date", value: formatDate(visit.visit_date) },
        { label: "Visit Type", value: getVisitTypeLabel(visit.visit_type) },
        {
          label: "Check-in Time",
          value: visit.check_in_time ? formatDateTime(visit.check_in_time) : null,
        },
        {
          label: "Consultation Start",
          value: visit.consultation_start_time
            ? formatDateTime(visit.consultation_start_time)
            : null,
        },
        {
          label: "Consultation End",
          value: visit.consultation_end_time ? formatDateTime(visit.consultation_end_time) : null,
        },
        {
          label: "Linked Appointment",
          value: visit.appointment_id ? (
            <Link
              href={`/dashboard/appointments/${visit.appointment_id}`}
              className="text-primary underline-offset-4 hover:underline"
            >
              View appointment
            </Link>
          ) : (
            "Walk-in (no linked appointment)"
          ),
        },
      ]}
    />
  );
}
