"use client";

import { Search } from "lucide-react";

import { Input } from "@/components/ui/input";

interface AppointmentSearchProps {
  value: string;
  onChange: (value: string) => void;
}

export function AppointmentSearch({ value, onChange }: AppointmentSearchProps) {
  return (
    <div className="relative max-w-sm flex-1">
      <Search
        className="absolute left-2.5 top-2.5 size-4 text-muted-foreground"
        aria-hidden="true"
      />
      <Input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Search by appointment ID, patient, or doctor..."
        className="pl-8"
        aria-label="Search appointments"
      />
    </div>
  );
}
