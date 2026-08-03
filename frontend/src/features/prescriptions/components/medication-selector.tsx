"use client";

import { ChevronsUpDown, Search } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useMedications } from "@/features/prescriptions/hooks/use-medications";
import { useDebounce } from "@/hooks/use-debounce";
import type { MedicationCatalogEntry } from "@/lib/mock/medications";

interface MedicationSelectorProps {
  onSelect: (medication: MedicationCatalogEntry) => void;
}

// A search-then-autofill tool, not a strict replacement for manual
// entry — picking a catalog entry here fans out to several fields at
// once (name, generic name, strength, route, dosage unit, frequency)
// via `onSelect`, but every field it fills stays a normal editable
// `FormInput`/`FormSelect` afterward, since this module's small mock
// catalog (`lib/mock/medications.ts`) can't cover every real medication
// a clinician might prescribe — this speeds up the common case, it
// doesn't gate it.
export function MedicationSelector({ onSelect }: MedicationSelectorProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounce(search, 200);
  const { data, isLoading } = useMedications({ search: debouncedSearch });
  const results = data ?? [];

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button type="button" variant="outline" size="sm" className="gap-2">
          <Search className="size-3.5" aria-hidden="true" />
          Search medications
          <ChevronsUpDown className="size-3.5 opacity-50" aria-hidden="true" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80 p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput placeholder="Search by name..." value={search} onValueChange={setSearch} />
          <CommandList>
            <CommandEmpty>{isLoading ? "Searching..." : "No medications found."}</CommandEmpty>
            <CommandGroup>
              {results.map((medication) => (
                <CommandItem
                  key={medication.medication_id}
                  value={medication.medication_id}
                  onSelect={() => {
                    onSelect(medication);
                    setOpen(false);
                    setSearch("");
                  }}
                >
                  <span>{medication.medication_name}</span>
                  {medication.generic_name && (
                    <span className="ml-auto text-xs text-muted-foreground">
                      {medication.generic_name}
                    </span>
                  )}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
