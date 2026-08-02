import { AlertCircle } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

interface ErrorAlertProps {
  title?: string;
  message?: string | null;
}

// Renders nothing when there's no message — safe to always mount at a
// fixed spot in a form and drive purely by state. The base `Alert`
// primitive sets `role="alert"` itself, so this is announced to screen
// readers the moment it appears, unlike a toast a user could miss.
export function ErrorAlert({ title = "Something went wrong", message }: ErrorAlertProps) {
  if (!message) return null;

  return (
    <Alert variant="destructive">
      <AlertCircle className="size-4" aria-hidden="true" />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  );
}
