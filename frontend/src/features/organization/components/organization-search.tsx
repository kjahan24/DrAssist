"use client";

import { Search } from "lucide-react";

import { Input } from "@/components/ui/input";

interface OrganizationSearchProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

// Shared by the Members, Departments, and Locations list pages — same
// generic search-input pattern every other module's own `*Search`
// component already uses, kept to one component in this module since
// all three lists search the same way (a free-text substring match).
export function OrganizationSearch({
  value,
  onChange,
  placeholder = "Search...",
}: OrganizationSearchProps) {
  return (
    <div className="relative max-w-sm flex-1">
      <Search
        className="absolute left-2.5 top-2.5 size-4 text-muted-foreground"
        aria-hidden="true"
      />
      <Input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="pl-8"
        aria-label={placeholder}
      />
    </div>
  );
}
