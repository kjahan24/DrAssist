"use client";

import { Search } from "lucide-react";

import { Input } from "@/components/ui/input";

interface SoapNoteSearchProps {
  value: string;
  onChange: (value: string) => void;
}

export function SoapNoteSearch({ value, onChange }: SoapNoteSearchProps) {
  return (
    <div className="relative max-w-sm flex-1">
      <Search
        className="absolute left-2.5 top-2.5 size-4 text-muted-foreground"
        aria-hidden="true"
      />
      <Input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Search by SOAP ID, patient, doctor, or visit..."
        className="pl-8"
        aria-label="Search SOAP notes"
      />
    </div>
  );
}
