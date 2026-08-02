"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { SOAPNoteStatus } from "@/lib/mock/soap-notes";

interface SoapNoteFiltersProps {
  status: SOAPNoteStatus | "all";
  onStatusChange: (status: SOAPNoteStatus | "all") => void;
}

export function SoapNoteFilters({ status, onStatusChange }: SoapNoteFiltersProps) {
  return (
    <Select
      value={status}
      onValueChange={(value) => onStatusChange(value as SOAPNoteStatus | "all")}
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
