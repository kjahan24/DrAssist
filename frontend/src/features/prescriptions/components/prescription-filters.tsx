"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { PrescriptionStatus } from "@/lib/mock/prescriptions";

interface PrescriptionFiltersProps {
  status: PrescriptionStatus | "all";
  onStatusChange: (status: PrescriptionStatus | "all") => void;
}

export function PrescriptionFilters({ status, onStatusChange }: PrescriptionFiltersProps) {
  return (
    <Select
      value={status}
      onValueChange={(value) => onStatusChange(value as PrescriptionStatus | "all")}
    >
      <SelectTrigger className="w-36" aria-label="Filter by status">
        <SelectValue placeholder="Status" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="all">All statuses</SelectItem>
        <SelectItem value="draft">Draft</SelectItem>
        <SelectItem value="final">Final</SelectItem>
      </SelectContent>
    </Select>
  );
}
