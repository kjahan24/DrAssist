"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export interface OrganizationFilterOption {
  label: string;
  value: string;
}

interface OrganizationFilterSpec {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: OrganizationFilterOption[];
  allLabel: string;
  className?: string;
}

interface OrganizationFiltersProps {
  filters: OrganizationFilterSpec[];
}

// A generic filter bar shared by the Members, Departments, and Locations
// list pages — each passes its own status/department option list rather
// than this module having three near-identical filter components, one
// per page.
export function OrganizationFilters({ filters }: OrganizationFiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {filters.map((filter) => (
        <Select key={filter.label} value={filter.value} onValueChange={filter.onChange}>
          <SelectTrigger className={filter.className ?? "w-40"} aria-label={filter.label}>
            <SelectValue placeholder={filter.label} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{filter.allLabel}</SelectItem>
            {filter.options.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      ))}
    </div>
  );
}
