"use client";

import { Check, ChevronsUpDown } from "lucide-react";
import { useState } from "react";
import type { Control, FieldPath, FieldValues } from "react-hook-form";

import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useDebounce } from "@/hooks/use-debounce";
import { usePatient, usePatients } from "@/features/patients/hooks/use-patients";
import { getFullName, type Patient } from "@/lib/mock/patients";
import { cn } from "@/lib/utils";

interface PatientComboboxFieldProps {
  value: string;
  onChange: (patientId: string) => void;
}

// Built from `Popover` + `Command` (the standard shadcn combobox
// composition) since the project has no dedicated `combobox.tsx`. A
// separate component (not an inline closure inside `FormField`'s
// `render`) so `usePatients`/`usePatient` are called at a stable
// component's top level rather than inside a render-prop callback.
function PatientComboboxField({ value, onChange }: PatientComboboxFieldProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounce(search, 200);
  const { data, isLoading } = usePatients({ search: debouncedSearch, page: 1, pageSize: 20 });
  // The list query above only covers the current search page — for an
  // already-selected patient (edit form, or after picking one) that may
  // have scrolled out of the current results, fall back to a direct
  // detail lookup so the trigger button always shows a real name instead
  // of a raw ID.
  const { data: selectedPatient } = usePatient(value);
  const results = data?.items ?? [];
  const selected: Patient | undefined =
    results.find((patient) => patient.patient_id === value) ?? selectedPatient ?? undefined;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <FormControl>
          <Button
            type="button"
            variant="outline"
            role="combobox"
            aria-expanded={open}
            className={cn("w-full justify-between font-normal", !value && "text-muted-foreground")}
          >
            <span className="truncate">
              {selected
                ? `${getFullName(selected)} · ${selected.patient_number}`
                : "Select a patient"}
            </span>
            <ChevronsUpDown className="ml-2 size-4 shrink-0 opacity-50" aria-hidden="true" />
          </Button>
        </FormControl>
      </PopoverTrigger>
      <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput
            placeholder="Search patients by name or ID..."
            value={search}
            onValueChange={setSearch}
          />
          <CommandList>
            <CommandEmpty>{isLoading ? "Searching..." : "No patients found."}</CommandEmpty>
            <CommandGroup>
              {results.map((patient) => (
                <CommandItem
                  key={patient.patient_id}
                  value={patient.patient_id}
                  onSelect={() => {
                    onChange(patient.patient_id);
                    setOpen(false);
                  }}
                >
                  <Check
                    className={cn(
                      "size-4",
                      patient.patient_id === value ? "opacity-100" : "opacity-0",
                    )}
                    aria-hidden="true"
                  />
                  <span>{getFullName(patient)}</span>
                  <span className="ml-auto text-xs text-muted-foreground">
                    {patient.patient_number}
                  </span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

interface PatientComboboxProps<TFieldValues extends FieldValues> {
  control: Control<TFieldValues>;
  name: FieldPath<TFieldValues>;
  label?: string;
}

export function PatientCombobox<TFieldValues extends FieldValues>({
  control,
  name,
  label = "Patient",
}: PatientComboboxProps<TFieldValues>) {
  return (
    <FormField
      control={control}
      name={name}
      render={({ field }) => (
        <FormItem className="flex flex-col">
          <FormLabel>{label}</FormLabel>
          <PatientComboboxField value={field.value} onChange={field.onChange} />
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
