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
import { useDoctor, useDoctors } from "@/features/appointments/hooks/use-doctors";
import type { Doctor } from "@/lib/mock/doctors";
import { cn } from "@/lib/utils";

interface DoctorComboboxFieldProps {
  value: string;
  onChange: (doctorId: string) => void;
}

function DoctorComboboxField({ value, onChange }: DoctorComboboxFieldProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounce(search, 200);
  const { data, isLoading } = useDoctors({ search: debouncedSearch });
  // Fallback for an already-selected doctor that may have scrolled out
  // of the current search results — see `PatientComboboxField`'s
  // identical reasoning.
  const { data: selectedDoctor } = useDoctor(value);
  const results = data ?? [];
  const selected: Doctor | undefined =
    results.find((doctor) => doctor.doctor_id === value) ?? selectedDoctor ?? undefined;

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
                ? `${selected.full_name} · ${selected.specialization_name}`
                : "Select a doctor"}
            </span>
            <ChevronsUpDown className="ml-2 size-4 shrink-0 opacity-50" aria-hidden="true" />
          </Button>
        </FormControl>
      </PopoverTrigger>
      <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput
            placeholder="Search doctors by name or specialty..."
            value={search}
            onValueChange={setSearch}
          />
          <CommandList>
            <CommandEmpty>{isLoading ? "Searching..." : "No doctors found."}</CommandEmpty>
            <CommandGroup>
              {results.map((doctor) => (
                <CommandItem
                  key={doctor.doctor_id}
                  value={doctor.doctor_id}
                  onSelect={() => {
                    onChange(doctor.doctor_id);
                    setOpen(false);
                  }}
                >
                  <Check
                    className={cn(
                      "size-4",
                      doctor.doctor_id === value ? "opacity-100" : "opacity-0",
                    )}
                    aria-hidden="true"
                  />
                  <span>{doctor.full_name}</span>
                  <span className="ml-auto text-xs text-muted-foreground">
                    {doctor.specialization_name}
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

interface DoctorComboboxProps<TFieldValues extends FieldValues> {
  control: Control<TFieldValues>;
  name: FieldPath<TFieldValues>;
  label?: string;
}

export function DoctorCombobox<TFieldValues extends FieldValues>({
  control,
  name,
  label = "Doctor",
}: DoctorComboboxProps<TFieldValues>) {
  return (
    <FormField
      control={control}
      name={name}
      render={({ field }) => (
        <FormItem className="flex flex-col">
          <FormLabel>{label}</FormLabel>
          <DoctorComboboxField value={field.value} onChange={field.onChange} />
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
