"use client";

import type { Control, FieldPath, FieldValues } from "react-hook-form";

import { FormSelect } from "@/components/shared/forms/form-select";
import { TIMEZONE_OPTIONS } from "@/lib/mock/settings";

interface TimezoneSelectorProps<TFieldValues extends FieldValues> {
  control: Control<TFieldValues>;
  name: FieldPath<TFieldValues>;
  label?: string;
}

// A `FormSelect` pre-populated with `TIMEZONE_OPTIONS` — the "Time Zone"
// field maps to the real `User.timezone` field (see
// `lib/mock/settings.ts`'s own docstring).
export function TimezoneSelector<TFieldValues extends FieldValues>({
  control,
  name,
  label = "Time Zone",
}: TimezoneSelectorProps<TFieldValues>) {
  return <FormSelect control={control} name={name} label={label} options={TIMEZONE_OPTIONS} />;
}
