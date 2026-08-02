"use client";

import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import type { Control, FieldPath, FieldValues } from "react-hook-form";

import { Button } from "@/components/ui/button";
import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";

interface PasswordInputProps<TFieldValues extends FieldValues> {
  control: Control<TFieldValues>;
  name: FieldPath<TFieldValues>;
  label?: string;
  description?: string;
  placeholder?: string;
  disabled?: boolean;
  autoComplete?: string;
}

// Same FormField/FormItem/FormLabel/FormControl/FormMessage composition
// `components/shared/forms/form-input.tsx` uses, plus a show/hide toggle
// — different enough from a plain text field (internal visibility state,
// a trailing icon button rendered inside the input) to warrant its own
// component rather than a variant of FormInput.
export function PasswordInput<TFieldValues extends FieldValues>({
  control,
  name,
  label,
  description,
  placeholder,
  disabled,
  autoComplete,
}: PasswordInputProps<TFieldValues>) {
  const [visible, setVisible] = useState(false);

  return (
    <FormField
      control={control}
      name={name}
      render={({ field }) => (
        <FormItem>
          {label && <FormLabel>{label}</FormLabel>}
          <FormControl>
            <div className="relative">
              <Input
                type={visible ? "text" : "password"}
                placeholder={placeholder}
                disabled={disabled}
                autoComplete={autoComplete}
                className="pr-10"
                {...field}
              />
              {/* Intentionally left in normal tab order — a visibility
                  toggle is a real interactive control keyboard users need
                  to reach, not decoration to skip past. */}
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="absolute right-0 top-0 h-full px-3 text-muted-foreground hover:bg-transparent"
                onClick={() => setVisible((prev) => !prev)}
                aria-label={visible ? "Hide password" : "Show password"}
                aria-pressed={visible}
              >
                {visible ? (
                  <EyeOff className="size-4" aria-hidden="true" />
                ) : (
                  <Eye className="size-4" aria-hidden="true" />
                )}
              </Button>
            </div>
          </FormControl>
          {description && <FormDescription>{description}</FormDescription>}
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
