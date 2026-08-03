"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DOCUMENT_CATEGORY_OPTIONS,
  DOCUMENT_STATUS_OPTIONS,
  type DocumentCategory,
  type DocumentStatus,
} from "@/lib/mock/documents";

interface DocumentFiltersProps {
  status: DocumentStatus | "all";
  onStatusChange: (status: DocumentStatus | "all") => void;
  category: DocumentCategory | "all";
  onCategoryChange: (category: DocumentCategory | "all") => void;
}

export function DocumentFilters({
  status,
  onStatusChange,
  category,
  onCategoryChange,
}: DocumentFiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Select
        value={category}
        onValueChange={(value) => onCategoryChange(value as DocumentCategory | "all")}
      >
        <SelectTrigger className="w-44" aria-label="Filter by category">
          <SelectValue placeholder="Category" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All categories</SelectItem>
          {DOCUMENT_CATEGORY_OPTIONS.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select
        value={status}
        onValueChange={(value) => onStatusChange(value as DocumentStatus | "all")}
      >
        <SelectTrigger className="w-36" aria-label="Filter by status">
          <SelectValue placeholder="Status" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All statuses</SelectItem>
          {DOCUMENT_STATUS_OPTIONS.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
