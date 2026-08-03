"use client";

import { CommandInput } from "@/components/ui/command";

interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
}

// A thin, named wrapper around `CommandInput` — must render inside a
// `Command`/`CommandDialog` (`cmdk` provides the search-box chrome and
// keyboard focus wiring already), kept as its own component only
// because this task's own reusable-component list names it distinctly.
export function SearchInput({ value, onChange }: SearchInputProps) {
  return (
    <CommandInput
      value={value}
      onValueChange={onChange}
      placeholder="Search patients, appointments, documents, and more..."
      aria-label="Global search"
    />
  );
}
