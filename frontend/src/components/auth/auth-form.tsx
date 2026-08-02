"use client";

import type { FieldValues, UseFormReturn } from "react-hook-form";

import { Form } from "@/components/ui/form";

interface AuthFormProps<TFieldValues extends FieldValues> {
  form: UseFormReturn<TFieldValues>;
  onSubmit: (values: TFieldValues) => void;
  children: React.ReactNode;
  className?: string;
}

// `noValidate` defers entirely to our own Zod/RHF validation
// (`FormMessage`) instead of also showing the browser's native HTML5
// validation bubbles, which would otherwise double up with — and often
// contradict — our own messages.
export function AuthForm<TFieldValues extends FieldValues>({
  form,
  onSubmit,
  children,
  className = "space-y-5",
}: AuthFormProps<TFieldValues>) {
  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className={className} noValidate>
        {children}
      </form>
    </Form>
  );
}
