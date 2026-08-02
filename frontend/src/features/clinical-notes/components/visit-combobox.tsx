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
import { useVisit, useVisits } from "@/features/visits/hooks/use-visits";
import { useDebounce } from "@/hooks/use-debounce";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";

interface VisitComboboxFieldProps {
  value: string;
  onChange: (visitId: string) => void;
}

// Same Popover+Command combobox pattern as `PatientCombobox`/
// `DoctorCombobox` (`features/appointments/components/`) and
// `AppointmentCombobox` (`features/visits/components/`) — unlike that
// last one, a clinical note's visit is required (the real entity's
// `visit_id` is non-nullable), so there's no "none" option here.
function VisitComboboxField({ value, onChange }: VisitComboboxFieldProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounce(search, 200);
  const { data, isLoading } = useVisits({ search: debouncedSearch, page: 1, pageSize: 20 });
  const { data: selectedVisit } = useVisit(value);
  const results = data?.items ?? [];
  const selected = results.find((visit) => visit.visit_id === value) ?? selectedVisit ?? undefined;

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
                ? `${selected.visit_number} · ${selected.patient_name} · ${formatDate(selected.visit_date)}`
                : "Select a visit"}
            </span>
            <ChevronsUpDown className="ml-2 size-4 shrink-0 opacity-50" aria-hidden="true" />
          </Button>
        </FormControl>
      </PopoverTrigger>
      <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput placeholder="Search visits..." value={search} onValueChange={setSearch} />
          <CommandList>
            <CommandEmpty>{isLoading ? "Searching..." : "No visits found."}</CommandEmpty>
            <CommandGroup>
              {results.map((visit) => (
                <CommandItem
                  key={visit.visit_id}
                  value={visit.visit_id}
                  onSelect={() => {
                    onChange(visit.visit_id);
                    setOpen(false);
                  }}
                >
                  <Check
                    className={cn("size-4", visit.visit_id === value ? "opacity-100" : "opacity-0")}
                    aria-hidden="true"
                  />
                  <span>{visit.visit_number}</span>
                  <span className="ml-auto text-xs text-muted-foreground">
                    {visit.patient_name} · {formatDate(visit.visit_date)}
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

interface VisitComboboxProps<TFieldValues extends FieldValues> {
  control: Control<TFieldValues>;
  name: FieldPath<TFieldValues>;
  label?: string;
}

export function VisitCombobox<TFieldValues extends FieldValues>({
  control,
  name,
  label = "Visit",
}: VisitComboboxProps<TFieldValues>) {
  return (
    <FormField
      control={control}
      name={name}
      render={({ field }) => (
        <FormItem className="flex flex-col">
          <FormLabel>{label}</FormLabel>
          <VisitComboboxField value={field.value} onChange={field.onChange} />
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
