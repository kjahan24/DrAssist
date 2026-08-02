"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { VISIT_TYPE_OPTIONS, type VisitStatus, type VisitType } from "@/lib/mock/visits";

interface VisitFiltersProps {
  status: VisitStatus | "all";
  onStatusChange: (status: VisitStatus | "all") => void;
  visitType: VisitType | "all";
  onVisitTypeChange: (type: VisitType | "all") => void;
}

export function VisitFilters({
  status,
  onStatusChange,
  visitType,
  onVisitTypeChange,
}: VisitFiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Select
        value={status}
        onValueChange={(value) => onStatusChange(value as VisitStatus | "all")}
      >
        <SelectTrigger className="w-36" aria-label="Filter by status">
          <SelectValue placeholder="Status" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All statuses</SelectItem>
          <SelectItem value="scheduled">Scheduled</SelectItem>
          <SelectItem value="checked_in">Checked In</SelectItem>
          <SelectItem value="in_progress">In Progress</SelectItem>
          <SelectItem value="completed">Completed</SelectItem>
          <SelectItem value="cancelled">Cancelled</SelectItem>
          <SelectItem value="no_show">No Show</SelectItem>
        </SelectContent>
      </Select>
      <Select
        value={visitType}
        onValueChange={(value) => onVisitTypeChange(value as VisitType | "all")}
      >
        <SelectTrigger className="w-40" aria-label="Filter by visit type">
          <SelectValue placeholder="Visit Type" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All visit types</SelectItem>
          {VISIT_TYPE_OPTIONS.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
