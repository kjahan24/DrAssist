"use client";

import type { Control, FieldPath, FieldValues } from "react-hook-form";

import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";

interface FormInputProps<TFieldValues extends FieldValues> {
  control: Control<TFieldValues>;
  name: FieldPath<TFieldValues>;
  label?: string;
  description?: string;
  type?: string;
  placeholder?: string;
  disabled?: boolean;
}

// Composes FormField/FormItem/FormLabel/FormControl/FormMessage
// (`components/ui/form.tsx`, shadcn's React Hook Form bindings) into one
// call so a typical field is one line in a feature form instead of five.
export function FormInput<TFieldValues extends FieldValues>({
  control,
  name,
  label,
  description,
  type = "text",
  placeholder,
  disabled,
}: FormInputProps<TFieldValues>) {
  return (
    <FormField
      control={control}
      name={name}
      render={({ field }) => (
        <FormItem>
          {label && <FormLabel>{label}</FormLabel>}
          <FormControl>
            <Input type={type} placeholder={placeholder} disabled={disabled} {...field} />
          </FormControl>
          {description && <FormDescription>{description}</FormDescription>}
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
