"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  LAB_REPORT_CATEGORY_OPTIONS,
  type LabReportCategory,
  type LabReportStatus,
} from "@/lib/mock/lab-reports";

interface LabReportFiltersProps {
  status: LabReportStatus | "all";
  onStatusChange: (status: LabReportStatus | "all") => void;
  category: LabReportCategory | "all";
  onCategoryChange: (category: LabReportCategory | "all") => void;
}

export function LabReportFilters({
  status,
  onStatusChange,
  category,
  onCategoryChange,
}: LabReportFiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Select
        value={status}
        onValueChange={(value) => onStatusChange(value as LabReportStatus | "all")}
      >
        <SelectTrigger className="w-36" aria-label="Filter by status">
          <SelectValue placeholder="Status" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All statuses</SelectItem>
          <SelectItem value="draft">Draft</SelectItem>
          <SelectItem value="ordered">Ordered</SelectItem>
          <SelectItem value="collected">Collected</SelectItem>
          <SelectItem value="final">Final</SelectItem>
          <SelectItem value="cancelled">Cancelled</SelectItem>
        </SelectContent>
      </Select>
      <Select
        value={category}
        onValueChange={(value) => onCategoryChange(value as LabReportCategory | "all")}
      >
        <SelectTrigger className="w-40" aria-label="Filter by category">
          <SelectValue placeholder="Category" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All categories</SelectItem>
          {LAB_REPORT_CATEGORY_OPTIONS.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
