"use client";

import type { Control, FieldPath, FieldValues } from "react-hook-form";

import { FormSelect } from "@/components/shared/forms/form-select";
import { LANGUAGE_OPTIONS } from "@/lib/mock/settings";

interface LanguageSelectorProps<TFieldValues extends FieldValues> {
  control: Control<TFieldValues>;
  name: FieldPath<TFieldValues>;
  label?: string;
}

// A `FormSelect` pre-populated with `LANGUAGE_OPTIONS` — the "Language"
// field maps to the real `User.locale` field (see
// `lib/mock/settings.ts`'s own docstring).
export function LanguageSelector<TFieldValues extends FieldValues>({
  control,
  name,
  label = "Language",
}: LanguageSelectorProps<TFieldValues>) {
  return <FormSelect control={control} name={name} label={label} options={LANGUAGE_OPTIONS} />;
}
