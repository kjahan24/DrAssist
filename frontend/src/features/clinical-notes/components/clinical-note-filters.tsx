"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  CLINICAL_NOTE_TYPE_OPTIONS,
  type ClinicalNoteStatus,
  type ClinicalNoteType,
} from "@/lib/mock/clinical-notes";

interface ClinicalNoteFiltersProps {
  status: ClinicalNoteStatus | "all";
  onStatusChange: (status: ClinicalNoteStatus | "all") => void;
  noteType: ClinicalNoteType | "all";
  onNoteTypeChange: (type: ClinicalNoteType | "all") => void;
}

export function ClinicalNoteFilters({
  status,
  onStatusChange,
  noteType,
  onNoteTypeChange,
}: ClinicalNoteFiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Select
        value={status}
        onValueChange={(value) => onStatusChange(value as ClinicalNoteStatus | "all")}
      >
        <SelectTrigger className="w-36" aria-label="Filter by status">
          <SelectValue placeholder="Status" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All statuses</SelectItem>
          <SelectItem value="draft">Draft</SelectItem>
          <SelectItem value="in_review">In Review</SelectItem>
          <SelectItem value="signed">Signed</SelectItem>
          <SelectItem value="locked">Locked</SelectItem>
        </SelectContent>
      </Select>
      <Select
        value={noteType}
        onValueChange={(value) => onNoteTypeChange(value as ClinicalNoteType | "all")}
      >
        <SelectTrigger className="w-40" aria-label="Filter by note type">
          <SelectValue placeholder="Note Type" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All note types</SelectItem>
          {CLINICAL_NOTE_TYPE_OPTIONS.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
