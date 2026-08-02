"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { GENDER_OPTIONS, type Gender, type PatientStatus } from "@/lib/mock/patients";

interface PatientFiltersProps {
  status: PatientStatus | "all";
  onStatusChange: (status: PatientStatus | "all") => void;
  gender: Gender | "all";
  onGenderChange: (gender: Gender | "all") => void;
}

export function PatientFilters({
  status,
  onStatusChange,
  gender,
  onGenderChange,
}: PatientFiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Select
        value={status}
        onValueChange={(value) => onStatusChange(value as PatientStatus | "all")}
      >
        <SelectTrigger className="w-36" aria-label="Filter by status">
          <SelectValue placeholder="Status" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All statuses</SelectItem>
          <SelectItem value="active">Active</SelectItem>
          <SelectItem value="inactive">Inactive</SelectItem>
        </SelectContent>
      </Select>
      <Select value={gender} onValueChange={(value) => onGenderChange(value as Gender | "all")}>
        <SelectTrigger className="w-36" aria-label="Filter by gender">
          <SelectValue placeholder="Gender" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All genders</SelectItem>
          {GENDER_OPTIONS.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
