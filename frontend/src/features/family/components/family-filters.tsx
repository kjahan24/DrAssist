"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  ACCESS_LEVEL_OPTIONS,
  FAMILY_ACCESS_STATUS_OPTIONS,
  RELATIONSHIP_OPTIONS,
  type AccessLevel,
  type FamilyAccessStatus,
  type Relationship,
} from "@/lib/mock/family-members";

interface FamilyFiltersProps {
  status: FamilyAccessStatus | "all";
  onStatusChange: (status: FamilyAccessStatus | "all") => void;
  accessLevel: AccessLevel | "all";
  onAccessLevelChange: (accessLevel: AccessLevel | "all") => void;
  relationship: Relationship | "all";
  onRelationshipChange: (relationship: Relationship | "all") => void;
}

export function FamilyFilters({
  status,
  onStatusChange,
  accessLevel,
  onAccessLevelChange,
  relationship,
  onRelationshipChange,
}: FamilyFiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Select
        value={relationship}
        onValueChange={(value) => onRelationshipChange(value as Relationship | "all")}
      >
        <SelectTrigger className="w-40" aria-label="Filter by relationship">
          <SelectValue placeholder="Relationship" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All relationships</SelectItem>
          {RELATIONSHIP_OPTIONS.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={accessLevel}
        onValueChange={(value) => onAccessLevelChange(value as AccessLevel | "all")}
      >
        <SelectTrigger className="w-44" aria-label="Filter by access level">
          <SelectValue placeholder="Access Level" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All access levels</SelectItem>
          {ACCESS_LEVEL_OPTIONS.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={status}
        onValueChange={(value) => onStatusChange(value as FamilyAccessStatus | "all")}
      >
        <SelectTrigger className="w-36" aria-label="Filter by status">
          <SelectValue placeholder="Status" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All statuses</SelectItem>
          {FAMILY_ACCESS_STATUS_OPTIONS.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
