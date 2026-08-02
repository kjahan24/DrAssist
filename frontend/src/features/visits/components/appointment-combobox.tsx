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
import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useAppointment, useAppointments } from "@/features/appointments/hooks/use-appointments";
import { useDebounce } from "@/hooks/use-debounce";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";

interface AppointmentComboboxFieldProps {
  value: string;
  onChange: (appointmentId: string) => void;
}

// Same Popover+Command combobox pattern as `PatientCombobox`/
// `DoctorCombobox` (`features/appointments/components/`, reused directly
// by `VisitForm` for the patient/doctor fields) — this one is new
// because linking a visit to an appointment is optional (a visit can be
// a walk-in), so it needs an explicit "No linked appointment" option
// rather than requiring a selection.
function AppointmentComboboxField({ value, onChange }: AppointmentComboboxFieldProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounce(search, 200);
  const { data, isLoading } = useAppointments({ search: debouncedSearch, page: 1, pageSize: 20 });
  const { data: selectedAppointment } = useAppointment(value);
  const results = data?.items ?? [];
  const selected =
    results.find((appointment) => appointment.appointment_id === value) ??
    selectedAppointment ??
    undefined;

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
                ? `${selected.appointment_number} · ${selected.patient_name} · ${formatDate(selected.appointment_date)}`
                : "No linked appointment"}
            </span>
            <ChevronsUpDown className="ml-2 size-4 shrink-0 opacity-50" aria-hidden="true" />
          </Button>
        </FormControl>
      </PopoverTrigger>
      <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput
            placeholder="Search appointments..."
            value={search}
            onValueChange={setSearch}
          />
          <CommandList>
            <CommandEmpty>{isLoading ? "Searching..." : "No appointments found."}</CommandEmpty>
            <CommandGroup>
              <CommandItem
                value="__none__"
                onSelect={() => {
                  onChange("");
                  setOpen(false);
                }}
              >
                <Check
                  className={cn("size-4", !value ? "opacity-100" : "opacity-0")}
                  aria-hidden="true"
                />
                <span className="text-muted-foreground">No linked appointment</span>
              </CommandItem>
              {results.map((appointment) => (
                <CommandItem
                  key={appointment.appointment_id}
                  value={appointment.appointment_id}
                  onSelect={() => {
                    onChange(appointment.appointment_id);
                    setOpen(false);
                  }}
                >
                  <Check
                    className={cn(
                      "size-4",
                      appointment.appointment_id === value ? "opacity-100" : "opacity-0",
                    )}
                    aria-hidden="true"
                  />
                  <span>{appointment.appointment_number}</span>
                  <span className="ml-auto text-xs text-muted-foreground">
                    {appointment.patient_name} · {formatDate(appointment.appointment_date)}
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

interface AppointmentComboboxProps<TFieldValues extends FieldValues> {
  control: Control<TFieldValues>;
  name: FieldPath<TFieldValues>;
  label?: string;
}

export function AppointmentCombobox<TFieldValues extends FieldValues>({
  control,
  name,
  label = "Linked Appointment",
}: AppointmentComboboxProps<TFieldValues>) {
  return (
    <FormField
      control={control}
      name={name}
      render={({ field }) => (
        <FormItem className="flex flex-col">
          <FormLabel>{label}</FormLabel>
          <AppointmentComboboxField value={field.value} onChange={field.onChange} />
          <FormDescription>Optional — leave unselected for a walk-in visit.</FormDescription>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
