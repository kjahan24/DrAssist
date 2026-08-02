"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  APPOINTMENT_TYPE_OPTIONS,
  type AppointmentStatus,
  type AppointmentType,
} from "@/lib/mock/appointments";

interface AppointmentFiltersProps {
  status: AppointmentStatus | "all";
  onStatusChange: (status: AppointmentStatus | "all") => void;
  appointmentType: AppointmentType | "all";
  onAppointmentTypeChange: (type: AppointmentType | "all") => void;
}

export function AppointmentFilters({
  status,
  onStatusChange,
  appointmentType,
  onAppointmentTypeChange,
}: AppointmentFiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Select
        value={status}
        onValueChange={(value) => onStatusChange(value as AppointmentStatus | "all")}
      >
        <SelectTrigger className="w-36" aria-label="Filter by status">
          <SelectValue placeholder="Status" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All statuses</SelectItem>
          <SelectItem value="scheduled">Scheduled</SelectItem>
          <SelectItem value="confirmed">Confirmed</SelectItem>
          <SelectItem value="checked_in">Checked In</SelectItem>
          <SelectItem value="in_progress">In Progress</SelectItem>
          <SelectItem value="completed">Completed</SelectItem>
          <SelectItem value="cancelled">Cancelled</SelectItem>
          <SelectItem value="no_show">No Show</SelectItem>
        </SelectContent>
      </Select>
      <Select
        value={appointmentType}
        onValueChange={(value) => onAppointmentTypeChange(value as AppointmentType | "all")}
      >
        <SelectTrigger className="w-40" aria-label="Filter by visit type">
          <SelectValue placeholder="Visit Type" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All visit types</SelectItem>
          {APPOINTMENT_TYPE_OPTIONS.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
