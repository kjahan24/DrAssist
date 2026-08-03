"use client";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  TIMELINE_EVENT_TYPE_OPTIONS,
  type TimelineEventType,
  type TimelineFilterOptions,
  type TimelineFilterState,
} from "@/lib/mock/timeline";

interface TimelineFiltersProps {
  filters: TimelineFilterState;
  onFiltersChange: (patch: Partial<TimelineFilterState>) => void;
  options: TimelineFilterOptions;
}

// Five filter dimensions (Date Range, Event Type, Doctor, Visit, Status)
// collapse into one `filters`/`onFiltersChange` pair instead of ten
// separate value/onChange props — every other module's filter bar only
// ever had one or two dimensions, so this is the first place a patch-object
// callback earns its keep over the usual per-field props.
export function TimelineFilters({ filters, onFiltersChange, options }: TimelineFiltersProps) {
  return (
    <div className="flex flex-wrap items-end gap-3">
      <div className="space-y-1.5">
        <Label htmlFor="timeline-filter-date-from" className="text-xs text-muted-foreground">
          From
        </Label>
        <Input
          id="timeline-filter-date-from"
          type="date"
          className="w-40"
          value={filters.dateFrom ?? ""}
          onChange={(event) => onFiltersChange({ dateFrom: event.target.value || undefined })}
        />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="timeline-filter-date-to" className="text-xs text-muted-foreground">
          To
        </Label>
        <Input
          id="timeline-filter-date-to"
          type="date"
          className="w-40"
          value={filters.dateTo ?? ""}
          onChange={(event) => onFiltersChange({ dateTo: event.target.value || undefined })}
        />
      </div>

      <Select
        value={filters.eventType ?? "all"}
        onValueChange={(value) =>
          onFiltersChange({ eventType: value as TimelineEventType | "all" })
        }
      >
        <SelectTrigger className="w-44" aria-label="Filter by event type">
          <SelectValue placeholder="Event Type" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All event types</SelectItem>
          {TIMELINE_EVENT_TYPE_OPTIONS.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={filters.doctorName ?? "all"}
        onValueChange={(value) => onFiltersChange({ doctorName: value })}
      >
        <SelectTrigger className="w-44" aria-label="Filter by doctor">
          <SelectValue placeholder="Doctor" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All doctors</SelectItem>
          {options.doctors.map((doctor) => (
            <SelectItem key={doctor} value={doctor}>
              {doctor}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={filters.visitId ?? "all"}
        onValueChange={(value) => onFiltersChange({ visitId: value })}
      >
        <SelectTrigger className="w-40" aria-label="Filter by visit">
          <SelectValue placeholder="Visit" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All visits</SelectItem>
          {options.visits.map((visit) => (
            <SelectItem key={visit.visit_id} value={visit.visit_id}>
              {visit.visit_number}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={filters.status ?? "all"}
        onValueChange={(value) => onFiltersChange({ status: value })}
      >
        <SelectTrigger className="w-36" aria-label="Filter by status">
          <SelectValue placeholder="Status" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All statuses</SelectItem>
          {options.statuses.map((status) => (
            <SelectItem key={status} value={status}>
              {status}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
