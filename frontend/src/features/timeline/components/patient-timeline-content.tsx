"use client";

import { AlertTriangle, Rows3, SquareStack } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { PageHeader } from "@/components/dashboard/page-header";
import { EmptyState } from "@/components/shared/states/empty-state";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TimelineDetailsPanel } from "@/features/timeline/components/timeline-details-panel";
import { TimelineEmptyState } from "@/features/timeline/components/timeline-empty-state";
import { TimelineFilters } from "@/features/timeline/components/timeline-filters";
import { TimelineLoading } from "@/features/timeline/components/timeline-loading";
import { TimelineSearch } from "@/features/timeline/components/timeline-search";
import { TimelineView } from "@/features/timeline/components/timeline-view";
import { usePatientTimeline } from "@/features/timeline/hooks/use-timeline";
import { usePatient } from "@/features/patients/hooks/use-patients";
import {
  filterTimelineEvents,
  getTimelineFilterOptions,
  type HealthTimelineEvent,
  type TimelineFilterState,
} from "@/lib/mock/timeline";
import { getFullName, getInitials } from "@/lib/mock/patients";

export function PatientTimelineContent({ patientId }: { patientId: string }) {
  const { data: patient, isLoading: isPatientLoading } = usePatient(patientId);
  const { data: events, isLoading: isTimelineLoading } = usePatientTimeline(patientId);

  const [view, setView] = useState<"timeline" | "compact">("timeline");
  const [filters, setFilters] = useState<TimelineFilterState>({});
  const [selectedEvent, setSelectedEvent] = useState<HealthTimelineEvent | null>(null);
  const [isPanelOpen, setIsPanelOpen] = useState(false);

  const allEvents = useMemo(() => events ?? [], [events]);
  const filterOptions = useMemo(() => getTimelineFilterOptions(allEvents), [allEvents]);
  const filteredEvents = useMemo(
    () => filterTimelineEvents(allEvents, filters),
    [allEvents, filters],
  );

  const isLoading = isPatientLoading || isTimelineLoading;

  if (!isPatientLoading && !patient) {
    return (
      <EmptyState
        titleAs="h1"
        icon={AlertTriangle}
        title="Patient not found"
        description="This patient may have been removed, or the link is incorrect."
      />
    );
  }

  function handleFiltersChange(patch: Partial<TimelineFilterState>) {
    setFilters((current) => ({ ...current, ...patch }));
  }

  function handleViewDetails(event: HealthTimelineEvent) {
    setSelectedEvent(event);
    setIsPanelOpen(true);
  }

  const hasAnyFilter = Boolean(
    filters.search ||
    (filters.eventType && filters.eventType !== "all") ||
    (filters.doctorName && filters.doctorName !== "all") ||
    (filters.visitId && filters.visitId !== "all") ||
    (filters.status && filters.status !== "all") ||
    filters.dateFrom ||
    filters.dateTo,
  );
  const showEmptyState = !isLoading && filteredEvents.length === 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title={patient ? `${getFullName(patient)}'s Health Timeline` : "Health Timeline"}
        description={
          patient
            ? `${patient.patient_number} · ${allEvents.length} recorded event${allEvents.length === 1 ? "" : "s"}`
            : undefined
        }
        actions={
          patient && (
            <div className="flex items-center gap-3">
              <Avatar className="hidden size-9 sm:flex">
                <AvatarFallback>{getInitials(patient)}</AvatarFallback>
              </Avatar>
              <Button variant="outline" asChild>
                <Link href={`/dashboard/patients/${patientId}`}>View Patient Record</Link>
              </Button>
            </div>
          )
        }
      />

      <div className="flex flex-col gap-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <TimelineSearch
            value={filters.search ?? ""}
            onChange={(value) => handleFiltersChange({ search: value })}
          />
          <Tabs value={view} onValueChange={(value) => setView(value as "timeline" | "compact")}>
            <TabsList>
              <TabsTrigger value="timeline" aria-label="Timeline view">
                <Rows3 className="size-4" />
                <span className="hidden sm:inline">Timeline</span>
              </TabsTrigger>
              <TabsTrigger value="compact" aria-label="Compact view">
                <SquareStack className="size-4" />
                <span className="hidden sm:inline">Compact</span>
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        <TimelineFilters
          filters={filters}
          onFiltersChange={handleFiltersChange}
          options={filterOptions}
        />
      </div>

      {isLoading ? (
        <TimelineLoading />
      ) : showEmptyState ? (
        <TimelineEmptyState variant={hasAnyFilter ? "no-results" : "empty"} />
      ) : (
        <TimelineView
          events={filteredEvents}
          compact={view === "compact"}
          onViewDetails={handleViewDetails}
        />
      )}

      <TimelineDetailsPanel
        event={selectedEvent}
        open={isPanelOpen}
        onOpenChange={setIsPanelOpen}
      />
    </div>
  );
}
