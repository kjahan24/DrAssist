"use client";

import { History, Search } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { PageHeader } from "@/components/dashboard/page-header";
import { CardSkeleton } from "@/components/shared/states/card-skeleton";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { usePatients } from "@/features/patients/hooks/use-patients";
import { useDebounce } from "@/hooks/use-debounce";
import { getAge, getFullName, getInitials } from "@/lib/mock/patients";

// The whole seeded patient roster comfortably fits in one page — this
// picker exists only to route into a specific patient's timeline, not to
// reproduce `/dashboard/patients`'s own full paginated list, so a
// generous single page (rather than real pagination) keeps it simple.
const PAGE_SIZE = 50;

// `/dashboard/timeline`'s landing page — mirrors every other module's
// list→detail pattern (e.g. Patients, Documents): pick a patient here,
// land on their full timeline at `/dashboard/timeline/[patientId]`.
export function TimelinePatientPicker() {
  const [searchInput, setSearchInput] = useState("");
  const debouncedSearch = useDebounce(searchInput, 300);

  const { data, isLoading } = usePatients({
    search: debouncedSearch,
    page: 1,
    pageSize: PAGE_SIZE,
  });
  const patients = data?.items ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Personal Health Timeline"
        description="Select a patient to view their complete chronological health history."
      />

      <div className="relative max-w-sm">
        <Search
          className="absolute left-2.5 top-2.5 size-4 text-muted-foreground"
          aria-hidden="true"
        />
        <Input
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
          placeholder="Search patients by name or ID..."
          className="pl-8"
          aria-label="Search patients"
        />
      </div>

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <CardSkeleton key={index} />
          ))}
        </div>
      ) : patients.length === 0 ? (
        <EmptyState
          icon={History}
          title="No patients found"
          description="Try a different search."
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {patients.map((patient) => (
            <Link
              key={patient.patient_id}
              href={`/dashboard/timeline/${patient.patient_id}`}
              className="block rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <Card className="h-full transition-colors hover:border-primary">
                <CardContent className="flex items-center gap-3 pt-6">
                  <Avatar className="size-10 shrink-0">
                    <AvatarFallback>{getInitials(patient)}</AvatarFallback>
                  </Avatar>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{getFullName(patient)}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      {patient.patient_number} · Age {getAge(patient.date_of_birth)}
                    </p>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
