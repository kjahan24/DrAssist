import Link from "next/link";
import { Users } from "lucide-react";

import { SectionCard } from "@/components/dashboard/section-card";
import { EmptyState } from "@/components/shared/states/empty-state";
import { TableSkeleton } from "@/components/shared/states/table-skeleton";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/format";
import type { RecentPatient } from "@/lib/mock/doctor-dashboard";

interface PatientListProps {
  patients: RecentPatient[];
  isLoading?: boolean;
}

export function PatientList({ patients, isLoading }: PatientListProps) {
  return (
    <SectionCard title="Recent Patients" description="Patients you've recently seen.">
      {isLoading ? (
        <TableSkeleton rows={4} columns={4} />
      ) : patients.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No recent patients"
          description="Patients you see will appear here."
        />
      ) : (
        <ul className="divide-y">
          {patients.map((patient) => (
            <li
              key={patient.patient_id}
              className="flex items-center gap-4 py-3 first:pt-0 last:pb-0"
            >
              <Avatar>
                <AvatarFallback>{patient.avatar_initials}</AvatarFallback>
              </Avatar>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{patient.full_name}</p>
                <p className="truncate text-xs capitalize text-muted-foreground">
                  {patient.age} yrs · {patient.gender} · Last visit{" "}
                  {formatDate(patient.last_visit_date)}
                </p>
              </div>
              <Button variant="outline" size="sm" asChild>
                <Link href={`/dashboard/patients/${patient.patient_id}`}>Open</Link>
              </Button>
            </li>
          ))}
        </ul>
      )}
    </SectionCard>
  );
}
