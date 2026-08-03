"use client";

import { Search } from "lucide-react";

import { Input } from "@/components/ui/input";

interface TimelineSearchProps {
  value: string;
  onChange: (value: string) => void;
}

export function TimelineSearch({ value, onChange }: TimelineSearchProps) {
  return (
    <div className="relative max-w-sm flex-1">
      <Search
        className="absolute left-2.5 top-2.5 size-4 text-muted-foreground"
        aria-hidden="true"
      />
      <Input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Search timeline events..."
        className="pl-8"
        aria-label="Search timeline events"
      />
    </div>
  );
}
